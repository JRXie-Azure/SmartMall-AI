package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 浼樻儬鍒?鎶樻墸鍒搞€? *
 * <p>瀵瑰簲 Python models.py 涓殑 Coupon銆俤iscount_type: fixed=鍥哄畾閲戦, percent=鐧惧垎姣斻€? */
@Entity
@Table(name = "coupons", indexes = {
        @Index(name = "idx_coupon_code", columnList = "code")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Coupon {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String code;

    @Column(nullable = false, length = 100)
    private String name;

    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String description = "";

    @Builder.Default
    @Column(name = "discount_type", length = 20)
    private String discountType = "fixed";

    @Column(name = "discount_value", nullable = false)
    private Double discountValue;

    @Builder.Default
    @Column(name = "min_order_amount")
    private Double minOrderAmount = 0.0;

    @Column(name = "max_discount")
    private Double maxDiscount;

    @Column(name = "valid_from")
    private LocalDateTime validFrom;

    @Column(name = "valid_until")
    private LocalDateTime validUntil;

    @Builder.Default
    @Column(name = "total_limit")
    private Integer totalLimit = 0;

    @Builder.Default
    @Column(name = "used_count")
    private Integer usedCount = 0;

    @Builder.Default
    @Column(name = "per_user_limit")
    private Integer perUserLimit = 1;

    @Builder.Default
    @Convert(converter = JsonConverters.LongListConverter.class)
    @Column(name = "applicable_products", columnDefinition = "TEXT")
    private List<Long> applicableProducts = new ArrayList<>();

    @Builder.Default
    @Convert(converter = JsonConverters.LongListConverter.class)
    @Column(name = "applicable_categories", columnDefinition = "TEXT")
    private List<Long> applicableCategories = new ArrayList<>();

    @Builder.Default
    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}