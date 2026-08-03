package com.smartmall.config;

import com.smartmall.common.ApiException;
import com.smartmall.security.JwtAuthenticationFilter;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;
import java.util.Map;

/**
 * 无状态 JWT 安全配置。
 *
 * <p>访问控制策略刻意与 Python 版保持一致：路由层面全部放行，
 * 具体的"是否需要登录/需要什么角色"由 {@code @CurrentUser} 与
 * {@code @PreAuthorize} 在方法上声明 —— 对应 FastAPI 的 Depends 写法。
 */
@Configuration
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final SmartMallProperties props;
    private final ObjectMapper objectMapper;

    /**
     * JwtAuthenticationFilter 是 @Component，Spring Boot 会把它自动注册进 Servlet 过滤器链，
     * 导致它在 Security 链内外各跑一次。这里显式关掉自动注册，只保留链内的那次。
     */
    @Bean
    public org.springframework.boot.web.servlet.FilterRegistrationBean<JwtAuthenticationFilter>
    disableAutoRegistration(JwtAuthenticationFilter filter) {
        var reg = new org.springframework.boot.web.servlet.FilterRegistrationBean<>(filter);
        reg.setEnabled(false);
        return reg;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        // 兼容 passlib 生成的 $2b$ 哈希，老用户密码无需重置
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(reg -> reg.anyRequest().permitAll())
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint((req, res, ex) ->
                                writeDetail(req, res, HttpStatus.UNAUTHORIZED, "Not authenticated"))
                        .accessDeniedHandler((req, res, ex) ->
                                writeDetail(req, res, HttpStatus.FORBIDDEN, "无权访问")))
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    private void writeDetail(HttpServletRequest req, jakarta.servlet.http.HttpServletResponse res,
                             HttpStatus fallbackStatus, String fallbackMsg) throws java.io.IOException {
        // 过滤器里记录的具体原因优先，保证错误文案与 Python 版一致
        Object err = req.getAttribute(JwtAuthenticationFilter.ATTR_AUTH_ERROR);
        int status = fallbackStatus.value();
        String msg = fallbackMsg;
        if (err instanceof ApiException apiEx) {
            status = apiEx.getStatus();
            msg = apiEx.getMessage();
        }
        res.setStatus(status);
        res.setContentType(MediaType.APPLICATION_JSON_VALUE);
        res.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(res.getWriter(), Map.of("detail", msg));
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration cfg = new CorsConfiguration();
        List<String> origins = props.getCors().originList();
        if (origins.size() == 1 && "*".equals(origins.get(0))) {
            // allowCredentials=true 时不能用 "*"，必须用 pattern
            cfg.setAllowedOriginPatterns(List.of("*"));
        } else {
            cfg.setAllowedOrigins(origins);
        }
        cfg.setAllowedMethods(List.of("*"));
        cfg.setAllowedHeaders(List.of("*"));
        cfg.setAllowCredentials(true);
        cfg.setExposedHeaders(List.of("X-Process-Time", "Retry-After"));
        cfg.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", cfg);
        return source;
    }
}
