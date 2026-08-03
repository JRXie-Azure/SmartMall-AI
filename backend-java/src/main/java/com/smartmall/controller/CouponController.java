package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.entity.Coupon;
import com.smartmall.entity.User;
import com.smartmall.entity.UserCoupon;
import com.smartmall.repository.CouponRepository;
import com.smartmall.repository.UserCouponRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 优惠券路由。
 *
 * <p>对应 Python routers/coupon.py。
 * 用户: 领取、查看我的优惠券、应用优惠券
 * 管理员: 创建优惠券
 */
@RestController
@RequestMapping("/api/coupons")
@RequiredArgsConstructor
public class CouponController {

    private final CouponRepository couponRepository;
    private final UserCouponRepository userCouponRepository;

    @GetMapping("/available")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listAvailable(@CurrentUser User user) {
        LocalDateTime now = LocalDateTime.now();
        List<Coupon> coupons = couponRepository.findByIsActiveTrue();

        List<Map<String, Object>> result = new ArrayList<>();
        for (Coupon c : coupons) {
            if (c.getValidFrom() != null && c.getValidFrom().isAfter(now)) continue;
            if (c.getValidUntil() != null && c.getValidUntil().isBefore(now)) continue;

            long userCount = userCouponRepository.countByUserIdAndCouponId(user.getId(), c.getId());
            if (userCount >= c.getPerUserLimit()) continue;

            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", c.getId());
            m.put("code", c.getCode());
            m.put("name", c.getName());
            m.put("description", c.getDescription());
            m.put("discount_type", c.getDiscountType());
            m.put("discount_value", c.getDiscountValue());
            m.put("min_order_amount", c.getMinOrderAmount());
            m.put("valid_until", c.getValidUntil());
            result.add(m);
        }
        return result;
    }

    @PostMapping("/claim/{couponId}")
    @Transactional
    public Map<String, Object> claimCoupon(@PathVariable Long couponId, @CurrentUser User user) {
        Coupon coupon = couponRepository.findById(couponId)
                .orElseThrow(() -> ApiException.notFound("优惠券不存在"));
        if (!Boolean.TRUE.equals(coupon.getIsActive())) {
            throw ApiException.notFound("优惠券不存在");
        }

        if (userCouponRepository.findByUserIdAndCouponId(user.getId(), couponId).isPresent()) {
            throw ApiException.badRequest("您已领取过该优惠券");
        }

        UserCoupon uc = UserCoupon.builder()
                .userId(user.getId())
                .couponId(couponId)
                .build();
        userCouponRepository.save(uc);
        return Map.of("message", "领取成功");
    }

    @GetMapping("/my")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> myCoupons(@CurrentUser User user) {
        return userCouponRepository.findByUserIdAndIsUsedFalse(user.getId()).stream()
                .map(uc -> {
                    Coupon c = couponRepository.findById(uc.getCouponId()).orElse(null);
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", uc.getId());
                    m.put("coupon_id", uc.getCouponId());
                    m.put("code", c != null ? c.getCode() : "");
                    m.put("name", c != null ? c.getName() : "");
                    m.put("discount_type", c != null ? c.getDiscountType() : "");
                    m.put("discount_value", c != null ? c.getDiscountValue() : 0);
                    m.put("min_order_amount", c != null ? c.getMinOrderAmount() : 0);
                    m.put("valid_until", c != null ? c.getValidUntil() : null);
                    return m;
                })
                .toList();
    }

    @PostMapping("/apply")
    @Transactional(readOnly = true)
    public Map<String, Object> applyCoupon(@RequestParam String code,
                                            @RequestParam double orderAmount,
                                            @CurrentUser User user) {
        Coupon coupon = couponRepository.findByCodeAndIsActiveTrue(code);
        if (coupon == null) {
            throw ApiException.notFound("优惠码无效");
        }

        LocalDateTime now = LocalDateTime.now();
        if (coupon.getValidFrom() != null && coupon.getValidFrom().isAfter(now)) {
            throw ApiException.badRequest("优惠券尚未生效");
        }
        if (coupon.getValidUntil() != null && coupon.getValidUntil().isBefore(now)) {
            throw ApiException.badRequest("优惠券已过期");
        }
        if (coupon.getMinOrderAmount() != null && coupon.getMinOrderAmount() > 0
                && orderAmount < coupon.getMinOrderAmount()) {
            throw ApiException.badRequest("订单金额需满¥" + coupon.getMinOrderAmount());
        }

        UserCoupon uc = userCouponRepository.findByUserIdAndCouponId(user.getId(), coupon.getId())
                .orElseThrow(() -> ApiException.badRequest("您未领取该优惠券"));
        if (Boolean.TRUE.equals(uc.getIsUsed())) {
            throw ApiException.badRequest("优惠券已使用");
        }

        double discount;
        if ("fixed".equals(coupon.getDiscountType())) {
            discount = Math.min(coupon.getDiscountValue(), orderAmount);
        } else {
            discount = orderAmount * (coupon.getDiscountValue() / 100);
            if (coupon.getMaxDiscount() != null) {
                discount = Math.min(discount, coupon.getMaxDiscount());
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("coupon_id", coupon.getId());
        result.put("code", coupon.getCode());
        result.put("name", coupon.getName());
        result.put("discount", Math.round(discount * 100.0) / 100.0);
        result.put("final_amount", Math.round((orderAmount - discount) * 100.0) / 100.0);
        return result;
    }

    @PostMapping("/admin/create")
    @Transactional
    public Map<String, Object> createCoupon(@RequestBody Map<String, Object> body,
                                            @CurrentUser User admin) {
        Roles.requireAdmin(admin);

        Coupon coupon = Coupon.builder()
                .code((String) body.getOrDefault("code", ""))
                .name((String) body.getOrDefault("name", ""))
                .description((String) body.getOrDefault("description", ""))
                .discountType((String) body.getOrDefault("discount_type", "fixed"))
                .discountValue(body.get("discount_value") != null ? ((Number) body.get("discount_value")).doubleValue() : 0)
                .minOrderAmount(body.get("min_order_amount") != null ? ((Number) body.get("min_order_amount")).doubleValue() : 0)
                .maxDiscount(body.get("max_discount") != null ? ((Number) body.get("max_discount")).doubleValue() : null)
                .totalLimit(body.get("total_limit") != null ? ((Number) body.get("total_limit")).intValue() : 0)
                .perUserLimit(body.get("per_user_limit") != null ? ((Number) body.get("per_user_limit")).intValue() : 1)
                .isActive(true)
                .build();
        coupon = couponRepository.save(coupon);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", coupon.getId());
        result.put("code", coupon.getCode());
        return result;
    }
}
