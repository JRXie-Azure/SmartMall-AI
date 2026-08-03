package com.smartmall.common;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartmall.config.SmartMallProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.http.MediaType;
import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * 滑动窗口限流，等价于 Python 版 RateLimitMiddleware。
 *
 * <p>Redis ZSET 优先（多实例共享），不可用时降级为进程内 Deque。
 * AI 接口（/api/ai/**）单独用更严格的配额，防止 LLM 被刷。
 */
@Slf4j
@Component
// -150: 日志之后、Security(-100) 之前拦截，超限请求不必走完整个认证链
@Order(-150)
public class RateLimitFilter extends OncePerRequestFilter {

    private final SmartMallProperties props;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    /** 内存降级存储: key -> 请求时间戳(毫秒)队列 */
    private final Map<String, Deque<Long>> memoryStore = new ConcurrentHashMap<>();

    public RateLimitFilter(SmartMallProperties props,
                           org.springframework.beans.factory.ObjectProvider<StringRedisTemplate> redisProvider,
                           ObjectMapper objectMapper) {
        this.props = props;
        this.redis = redisProvider.getIfAvailable();
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain chain) throws ServletException, IOException {

        SmartMallProperties.RateLimit cfg = props.getRateLimit();
        String path = request.getRequestURI();

        // 只限 API；静态资源、前端页面、健康检查直接放行
        if (!cfg.isEnabled() || !path.startsWith("/api/") || "/api/health".equals(path)) {
            chain.doFilter(request, response);
            return;
        }

        int limit = path.startsWith("/api/ai/") ? cfg.getAiRequests() : cfg.getRequests();
        int window = cfg.getWindowSeconds();
        String key = "ratelimit:" + clientIp(request) + ":" + path;

        boolean allowed = (redis != null)
                ? checkRedis(key, limit, window)
                : checkMemory(key, limit, window);

        if (!allowed) {
            log.warn("Rate limit exceeded: {} -> {}", clientIp(request), path);
            response.setStatus(429);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.setCharacterEncoding("UTF-8");
            response.setHeader("Retry-After", String.valueOf(window));
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("detail", "请求过于频繁，请稍后再试");
            body.put("retry_after", window);
            body.put("limit", limit);
            body.put("window", window);
            objectMapper.writeValue(response.getWriter(), body);
            return;
        }

        chain.doFilter(request, response);
    }

    private boolean checkRedis(String key, int limit, int window) {
        try {
            long nowMs = System.currentTimeMillis();
            ZSetOperations<String, String> zset = redis.opsForZSet();
            zset.removeRangeByScore(key, 0, nowMs - window * 1000L);
            zset.add(key, nowMs + ":" + Math.random(), nowMs);
            Long count = zset.zCard(key);
            redis.expire(key, window, TimeUnit.SECONDS);
            return count == null || count <= limit;
        } catch (Exception e) {
            log.warn("Redis 限流失败，降级为内存限流: {}", e.getMessage());
            return checkMemory(key, limit, window);
        }
    }

    private boolean checkMemory(String key, int limit, int window) {
        long now = System.currentTimeMillis();
        long cutoff = now - window * 1000L;
        Deque<Long> store = memoryStore.computeIfAbsent(key, k -> new ArrayDeque<>());
        synchronized (store) {
            while (!store.isEmpty() && store.peekFirst() < cutoff) {
                store.pollFirst();
            }
            if (store.size() >= limit) {
                return false;
            }
            store.addLast(now);
            return true;
        }
    }

    private static String clientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            int comma = xff.indexOf(',');
            return (comma > 0 ? xff.substring(0, comma) : xff).trim();
        }
        String real = request.getHeader("X-Real-IP");
        if (real != null && !real.isBlank()) {
            return real.trim();
        }
        String addr = request.getRemoteAddr();
        return addr == null ? "unknown" : addr;
    }
}
