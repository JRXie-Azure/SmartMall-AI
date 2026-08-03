package com.smartmall.config;

import com.smartmall.websocket.ChatWebSocketHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.server.standard.ServletServerContainerFactoryBean;

/**
 * 原生 WebSocket 端点注册（不用 STOMP —— 前端 index.html 直接 new WebSocket 收发 JSON）。
 *
 * <p>WebSocketHandlerMapping 的 order 是 1，优先级高于 WebMvcConfig 里
 * 那个兜底的 {@code /**} 静态资源 handler，所以 /ws/chat 不会被静态资源拦走。
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final ChatWebSocketHandler chatWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatWebSocketHandler, "/ws/chat")
                // 与 CORS 策略一致：允许任意来源接入（凭证走 JWT，不依赖 Cookie）
                .setAllowedOriginPatterns("*");
    }

    /** 放宽帧大小与空闲超时，AI 回复偶尔会很长 */
    @Bean
    public ServletServerContainerFactoryBean createWebSocketContainer() {
        ServletServerContainerFactoryBean container = new ServletServerContainerFactoryBean();
        container.setMaxTextMessageBufferSize(64 * 1024);
        container.setMaxBinaryMessageBufferSize(64 * 1024);
        container.setMaxSessionIdleTimeout(30 * 60 * 1000L);
        return container;
    }
}
