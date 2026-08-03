package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 钀ラ攢娲诲姩 (闄愭椂鎶樻墸/婊″噺/绉掓潃)銆? *
 * <p>瀵瑰簲 Python models.py 涓殑 MarketingCampaign銆? * campaign_type: discount / flash_sale / full_reduction
 */
@Entity
@Table(name = "marketing_campaigns")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MarketingCampaign {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String name;

    @Builder.Default
    @Column(name = "campaign_type", length = 30)
    private String campaignType = "discount";

    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String description = "";

    @Builder.Default
    @Column(name = "banner_image", length = 500)
    private String bannerImage = "";

    @Builder.Default
    @Column(name = "discount_value")
    private Double discountValue = 0.0;

    @Builder.Default
    @Column(name = "min_order_amount")
    private Double minOrderAmount = 0.0;

    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

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