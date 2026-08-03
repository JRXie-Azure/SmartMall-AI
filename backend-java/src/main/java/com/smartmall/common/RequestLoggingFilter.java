package com.smartmall.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/** 请求日志 + X-Process-Time 响应头，对应 Python 版 RequestLoggingMiddleware */
@Slf4j
@Component
// -200: 排在 Security 过滤器链 (默认 -100) 之前，与 Python 版中间件顺序一致
@Order(-200)
public class RequestLoggingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain chain) throws ServletException, IOException {
        long start = System.nanoTime();
        try {
            chain.doFilter(request, response);
        } finally {
            long ms = (System.nanoTime() - start) / 1_000_000;
            String path = request.getRequestURI();
            if (!response.isCommitted()) {
                response.setHeader("X-Process-Time", ms + "ms");
            }
            if (path.startsWith("/api/")) {
                log.info("{} {} -> {} ({}ms)", request.getMethod(), path, response.getStatus(), ms);
            }
        }
    }
}
