package com.smartmall.common;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartmall.config.SmartMallProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 缓存服务：Redis 优先，不可用时自动降级为进程内内存缓存。
 * 对应原 Python 版 app/database.py 中的 cache_get / cache_set / cache_delete_pattern。
 */
@Slf4j
@Service
public class CacheService {

    private final StringRedisTemplate redis;
    private final SmartMallProperties props;
    private final ObjectMapper mapper;

    /** 内存兜底: key -> (json, 过期时间戳ms) */
    private final Map<String, Object[]> memory = new ConcurrentHashMap<>();

    /** Redis 探活结果，失败后不再反复重试拖慢请求 */
    private volatile Boolean redisHealthy = null;

    public CacheService(StringRedisTemplate redis, SmartMallProperties props, ObjectMapper mapper) {
        this.redis = redis;
        this.props = props;
        this.mapper = mapper;
    }

    public boolean redisAvailable() {
        if (!props.getCache().isRedisEnabled()) {
            return false;
        }
        if (redisHealthy == null) {
            synchronized (this) {
                if (redisHealthy == null) {
                    try {
                        redis.hasKey("__smartmall_ping__");
                        redisHealthy = true;
                        log.info("Redis 连接成功");
                    } catch (Exception e) {
                        redisHealthy = false;
                        log.warn("Redis 连接失败，降级为内存缓存: {}", e.getMessage());
                    }
                }
            }
        }
        return redisHealthy;
    }

    public <T> T get(String key, TypeReference<T> type) {
        String raw = getRaw(key);
        if (raw == null) {
            return null;
        }
        try {
            return mapper.readValue(raw, type);
        } catch (Exception e) {
            log.warn("缓存反序列化失败 key={}", key, e);
            return null;
        }
    }

    private String getRaw(String key) {
        if (redisAvailable()) {
            try {
                return redis.opsForValue().get(key);
            } catch (Exception e) {
                log.warn("Redis 读取失败，降级内存: {}", e.getMessage());
                redisHealthy = false;
            }
        }
        Object[] entry = memory.get(key);
        if (entry == null) {
            return null;
        }
        if (System.currentTimeMillis() > (Long) entry[1]) {
            memory.remove(key);
            return null;
        }
        return (String) entry[0];
    }

    public void set(String key, Object value) {
        set(key, value, props.getCache().getExpireSeconds());
    }

    public void set(String key, Object value, long expireSeconds) {
        String json;
        try {
            json = mapper.writeValueAsString(value);
        } catch (Exception e) {
            log.warn("缓存序列化失败 key={}", key, e);
            return;
        }
        if (redisAvailable()) {
            try {
                redis.opsForValue().set(key, json, Duration.ofSeconds(expireSeconds));
                return;
            } catch (Exception e) {
                log.warn("Redis 写入失败，降级内存: {}", e.getMessage());
                redisHealthy = false;
            }
        }
        memory.put(key, new Object[]{json, System.currentTimeMillis() + expireSeconds * 1000});
    }

    public void delete(String key) {
        if (redisAvailable()) {
            try {
                redis.delete(key);
            } catch (Exception e) {
                log.warn("Redis 删除失败: {}", e.getMessage());
            }
        }
        memory.remove(key);
    }

    /** 批量删除，pattern 形如 "products:*" */
    public void deletePattern(String pattern) {
        if (redisAvailable()) {
            try {
                Set<String> keys = redis.keys(pattern);
                if (keys != null && !keys.isEmpty()) {
                    redis.delete(keys);
                }
            } catch (Exception e) {
                log.warn("Redis 批量删除失败: {}", e.getMessage());
            }
        }
        String prefix = pattern.endsWith("*") ? pattern.substring(0, pattern.length() - 1) : pattern;
        memory.keySet().removeIf(k -> k.startsWith(prefix));
    }
}
