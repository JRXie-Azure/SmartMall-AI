package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 商品。
 *
 * <p>价格用 Double 而非 BigDecimal —— 这是刻意为之：原 Python 版用的是 float，
 * JSON 输出形如 799.0，改成 BigDecimal 会变成 799.00 从而破坏前端契约。
 * 若后续要做真实资金结算，应连同前端一起切换到 BigDecimal + 分为单位。
 */
@Entity
@Table(name = "products", indexes = {
        @Index(name = "idx_product_name", columnList = "name"),
        @Index(name = "idx_product_category", columnList = "category_id"),
        @Index(name = "idx_product_active_audit", columnList = "is_active,audit_status")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 300)
    private String name;

    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String description = "";

    @Column(nullable = false)
    private Double price;

    @Column(name = "original_price")
    private Double originalPrice;

    @Builder.Default
    @Column(length = 500)
    private String image = "";

    @Builder.Default
    @Convert(converter = JsonConverters.StringListConverter.class)
    @Column(columnDefinition = "TEXT")
    private List<String> images = new ArrayList<>();

    @Builder.Default
    private Integer stock = 0;

    @Builder.Default
    private Integer sales = 0;

    @Column(name = "category_id")
    private Long categoryId;

    @Builder.Default
    @Convert(converter = JsonConverters.StringListConverter.class)
    @Column(columnDefinition = "TEXT")
    private List<String> tags = new ArrayList<>();

    @Builder.Default
    @Column(length = 100)
    private String brand = "";

    @Builder.Default
    private Double rating = 5.0;

    @Builder.Default
    @Column(name = "is_recommend")
    private Boolean isRecommend = false;

    @Builder.Default
    @Column(name = "is_new")
    private Boolean isNew = false;

    @Builder.Default
    @Column(name = "is_sale")
    private Boolean isSale = false;

    @Builder.Default
    @Column(name = "is_active")
    private Boolean isActive = true;

    /** pending / approved / rejected */
    @Builder.Default
    @Column(name = "audit_status", length = 20)
    private String auditStatus = "approved";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
