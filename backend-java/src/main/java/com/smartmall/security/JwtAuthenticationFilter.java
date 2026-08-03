package com.smartmall.security;

import com.smartmall.common.ApiException;
import com.smartmall.entity.User;
import com.smartmall.repository.UserRepository;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Optional;

/**
 * 解析 Bearer Token 并填充 SecurityContext。
 *
 * <p>这里刻意"不抛异常"：Token 缺失或非法都只是不认证，把具体的 401/403 决策
 * 留给 {@link CurrentUserArgumentResolver}，这样才能同时支持
 * get_current_user（必须登录）和 get_current_user_optional（可匿名）两种语义。
 * 失败原因写入 request attribute，供 resolver 还原成与 Python 一致的错误文案。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    /** 认证失败原因，值为 ApiException */
    public static final String ATTR_AUTH_ERROR = "smartmall.auth.error";

    private final JwtService jwtService;
    private final UserRepository userRepository;

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain chain) throws ServletException, IOException {

        String token = resolveToken(request);
        if (token == null) {
            chain.doFilter(request, response);
            return;
        }

        try {
            Claims claims = jwtService.parse(token);
            String sub = claims.getSubject();
            if (sub == null || sub.isBlank()) {
                request.setAttribute(ATTR_AUTH_ERROR, ApiException.unauthorized("无效的认证凭证"));
                chain.doFilter(request, response);
                return;
            }

            Optional<User> found = userRepository.findById(Long.valueOf(sub));
            if (found.isEmpty()) {
                request.setAttribute(ATTR_AUTH_ERROR, ApiException.unauthorized("无效的认证凭证"));
                chain.doFilter(request, response);
                return;
            }

            User user = found.get();
            if (!Boolean.TRUE.equals(user.getIsActive())) {
                request.setAttribute(ATTR_AUTH_ERROR, ApiException.forbidden("账号已被禁用"));
                chain.doFilter(request, response);
                return;
            }

            AuthUser principal = new AuthUser(user);
            var auth = new UsernamePasswordAuthenticationToken(
                    principal, null, principal.getAuthorities());
            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(auth);

        } catch (JwtException | NumberFormatException e) {
            request.setAttribute(ATTR_AUTH_ERROR, ApiException.unauthorized("Token 无效或已过期"));
        }

        chain.doFilter(request, response);
    }

    private String resolveToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            String t = header.substring(7).trim();
            return t.isEmpty() ? null : t;
        }
        // WebSocket 握手常用 query 传参，兼容 ?token=xxx
        String q = request.getParameter("token");
        return (q == null || q.isBlank()) ? null : q;
    }
}
