package com.smartmall.controller;

import com.smartmall.entity.SiteConfig;
import com.smartmall.entity.User;
import com.smartmall.repository.SiteConfigRepository;
import com.smartmall.common.ApiException;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 系统配置管理 (键值对)。
 *
 * <p>公开接口: GET /api/site-config/{key} — 获取配置值
 * 管理接口: GET/PUT /api/site-config — 需 admin 角色
 */
@RestController
@RequestMapping("/api/site-config")
@RequiredArgsConstructor
public class SiteConfigController {

    private final SiteConfigRepository configRepository;

    @GetMapping("/{key}")
    @Transactional(readOnly = true)
    public Map<String, Object> get(@PathVariable String key) {
        SiteConfig config = configRepository.findByConfigKey(key)
                .orElseThrow(() -> ApiException.notFound("配置项不存在"));
        return toMap(config);
    }

    @GetMapping
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listAll(@CurrentUser User admin) {
        Roles.requireAdmin(admin);
        return configRepository.findAll().stream()
                .map(this::toMap)
                .toList();
    }

    @PutMapping("/{key}")
    @Transactional
    public Map<String, Object> upsert(@PathVariable String key, @RequestBody Map<String, Object> body,
                                      @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        String value = (String) body.getOrDefault("value", "");
        String description = (String) body.getOrDefault("description", "");

        SiteConfig config = configRepository.findByConfigKey(key).orElse(null);
        if (config == null) {
            config = SiteConfig.builder()
                    .configKey(key)
                    .configValue(value)
                    .description(description)
                    .build();
        } else {
            config.setConfigValue(value);
            if (!description.isBlank()) {
                config.setDescription(description);
            }
        }
        config = configRepository.save(config);
        return toMap(config);
    }

    private Map<String, Object> toMap(SiteConfig c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", c.getId());
        m.put("config_key", c.getConfigKey());
        m.put("config_value", c.getConfigValue());
        m.put("description", c.getDescription());
        m.put("updated_at", c.getUpdatedAt());
        return m;
    }
}
