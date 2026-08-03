package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.entity.Banner;
import com.smartmall.entity.User;
import com.smartmall.repository.BannerRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 首页轮播图管理。
 *
 * <p>公开接口: GET /api/banners — 获取活跃轮播图
 * 管理接口: POST/PUT/DELETE — 需 admin 角色
 */
@RestController
@RequestMapping("/api/banners")
@RequiredArgsConstructor
public class BannerController {

    private final BannerRepository bannerRepository;

    @GetMapping
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listActive() {
        return bannerRepository.findByIsActiveTrueOrderBySortOrderAsc().stream()
                .map(this::toMap)
                .toList();
    }

    @GetMapping("/all")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listAll(@CurrentUser User admin) {
        Roles.requireAdmin(admin);
        return bannerRepository.findAll().stream()
                .map(this::toMap)
                .toList();
    }

    @PostMapping
    @Transactional
    public Map<String, Object> create(@RequestBody Map<String, Object> body, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        String image = (String) body.get("image");
        if (image == null || image.isBlank()) {
            throw ApiException.badRequest("图片不能为空");
        }
        Banner banner = Banner.builder()
                .title((String) body.getOrDefault("title", ""))
                .image(image)
                .link((String) body.getOrDefault("link", ""))
                .sortOrder(body.get("sort_order") != null ? ((Number) body.get("sort_order")).intValue() : 0)
                .isActive(body.get("is_active") != null ? (Boolean) body.get("is_active") : true)
                .build();
        banner = bannerRepository.save(banner);
        return toMap(banner);
    }

    @PutMapping("/{id}")
    @Transactional
    public Map<String, Object> update(@PathVariable Long id, @RequestBody Map<String, Object> body,
                                      @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Banner banner = bannerRepository.findById(id)
                .orElseThrow(() -> ApiException.notFound("Banner不存在"));
        if (body.containsKey("title")) banner.setTitle((String) body.get("title"));
        if (body.containsKey("image")) banner.setImage((String) body.get("image"));
        if (body.containsKey("link")) banner.setLink((String) body.get("link"));
        if (body.get("sort_order") != null) banner.setSortOrder(((Number) body.get("sort_order")).intValue());
        if (body.containsKey("is_active")) banner.setIsActive((Boolean) body.get("is_active"));
        banner = bannerRepository.save(banner);
        return toMap(banner);
    }

    @DeleteMapping("/{id}")
    @Transactional
    public Map<String, Object> delete(@PathVariable Long id, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Banner banner = bannerRepository.findById(id)
                .orElseThrow(() -> ApiException.notFound("Banner不存在"));
        banner.setIsActive(false);
        bannerRepository.save(banner);
        return Map.of("message", "已下架");
    }

    private Map<String, Object> toMap(Banner b) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", b.getId());
        m.put("title", b.getTitle());
        m.put("image", b.getImage());
        m.put("link", b.getLink());
        m.put("sort_order", b.getSortOrder());
        m.put("is_active", b.getIsActive());
        m.put("created_at", b.getCreatedAt());
        return m;
    }
}
