package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.entity.MarketingCampaign;
import com.smartmall.entity.User;
import com.smartmall.repository.MarketingCampaignRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 营销活动管理。
 *
 * <p>公开接口: GET /api/marketing/campaigns — 获取活跃活动
 * 管理接口: POST/PUT/DELETE — 需 admin 角色
 */
@RestController
@RequestMapping("/api/marketing")
@RequiredArgsConstructor
public class MarketingController {

    private final MarketingCampaignRepository campaignRepository;

    @GetMapping("/campaigns")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listActive() {
        return campaignRepository.findByIsActiveTrue().stream()
                .map(this::toMap)
                .toList();
    }

    @GetMapping("/campaigns/all")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listAll(@CurrentUser User admin) {
        Roles.requireAdmin(admin);
        return campaignRepository.findAll().stream()
                .map(this::toMap)
                .toList();
    }

    @PostMapping("/campaigns")
    @Transactional
    public Map<String, Object> create(@RequestBody Map<String, Object> body, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        String name = (String) body.get("name");
        if (name == null || name.isBlank()) {
            throw ApiException.badRequest("活动名称不能为空");
        }
        MarketingCampaign campaign = MarketingCampaign.builder()
                .name(name)
                .campaignType((String) body.getOrDefault("campaign_type", "discount"))
                .description((String) body.getOrDefault("description", ""))
                .bannerImage((String) body.getOrDefault("banner_image", ""))
                .discountValue(body.get("discount_value") != null ? ((Number) body.get("discount_value")).doubleValue() : 0)
                .minOrderAmount(body.get("min_order_amount") != null ? ((Number) body.get("min_order_amount")).doubleValue() : 0)
                .startTime(body.get("start_time") != null ? LocalDateTime.parse(body.get("start_time").toString()) : LocalDateTime.now())
                .endTime(body.get("end_time") != null ? LocalDateTime.parse(body.get("end_time").toString()) : LocalDateTime.now().plusDays(7))
                .isActive(body.get("is_active") != null ? (Boolean) body.get("is_active") : true)
                .build();
        campaign = campaignRepository.save(campaign);
        return toMap(campaign);
    }

    @PutMapping("/campaigns/{id}")
    @Transactional
    public Map<String, Object> update(@PathVariable Long id, @RequestBody Map<String, Object> body,
                                      @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        MarketingCampaign campaign = campaignRepository.findById(id)
                .orElseThrow(() -> ApiException.notFound("活动不存在"));
        if (body.containsKey("name")) campaign.setName((String) body.get("name"));
        if (body.containsKey("campaign_type")) campaign.setCampaignType((String) body.get("campaign_type"));
        if (body.containsKey("description")) campaign.setDescription((String) body.get("description"));
        if (body.containsKey("banner_image")) campaign.setBannerImage((String) body.get("banner_image"));
        if (body.get("discount_value") != null) campaign.setDiscountValue(((Number) body.get("discount_value")).doubleValue());
        if (body.get("min_order_amount") != null) campaign.setMinOrderAmount(((Number) body.get("min_order_amount")).doubleValue());
        if (body.get("start_time") != null) campaign.setStartTime(LocalDateTime.parse(body.get("start_time").toString()));
        if (body.get("end_time") != null) campaign.setEndTime(LocalDateTime.parse(body.get("end_time").toString()));
        if (body.containsKey("is_active")) campaign.setIsActive((Boolean) body.get("is_active"));
        campaign = campaignRepository.save(campaign);
        return toMap(campaign);
    }

    @DeleteMapping("/campaigns/{id}")
    @Transactional
    public Map<String, Object> delete(@PathVariable Long id, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        MarketingCampaign campaign = campaignRepository.findById(id)
                .orElseThrow(() -> ApiException.notFound("活动不存在"));
        campaign.setIsActive(false);
        campaignRepository.save(campaign);
        return Map.of("message", "活动已下线");
    }

    private Map<String, Object> toMap(MarketingCampaign c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", c.getId());
        m.put("name", c.getName());
        m.put("campaign_type", c.getCampaignType());
        m.put("description", c.getDescription());
        m.put("banner_image", c.getBannerImage());
        m.put("discount_value", c.getDiscountValue());
        m.put("min_order_amount", c.getMinOrderAmount());
        m.put("start_time", c.getStartTime());
        m.put("end_time", c.getEndTime());
        m.put("applicable_products", c.getApplicableProducts());
        m.put("applicable_categories", c.getApplicableCategories());
        m.put("is_active", c.getIsActive());
        m.put("created_at", c.getCreatedAt());
        return m;
    }
}
