package com.smartmall.controller;

import com.smartmall.config.SmartMallProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;

/** 健康检查，字段与 Python 版 /api/health 完全一致 */
@RestController
@RequiredArgsConstructor
public class SystemController {

    private final SmartMallProperties props;

    @Value("${spring.datasource.url:}")
    private String datasourceUrl;

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "ok");
        body.put("version", props.getAppVersion());
        body.put("llm_enabled", props.getLlm().enabled());
        body.put("llm_model", props.getLlm().enabled() ? props.getLlm().model() : null);
        body.put("database", datasourceUrl.startsWith("jdbc:mysql") ? "MySQL" : "H2");
        body.put("rate_limit", props.getRateLimit().isEnabled() ? "enabled" : "disabled");
        return body;
    }

    /** 根路径重定向到 index.html */
    @GetMapping("/")
    public ResponseEntity<Void> rootRedirect() {
        return ResponseEntity.status(302).location(URI.create("/index.html")).build();
    }
}
