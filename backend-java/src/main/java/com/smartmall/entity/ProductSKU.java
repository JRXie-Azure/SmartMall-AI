package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 鍟嗗搧瑙勬牸 SKU (棰滆壊/灏哄绛夊彉浣?銆? *
 * <p>瀵瑰簲 Python models.py 涓殑 ProductSKU锛宎ttributes 鐢?JSON 瀛樺偍瑙勬牸閿€煎銆? */
@Entity
@Table(name = "product_skus", indexes = {
        @Index(name = "idx_sku_product", columnList = "product_id"),
        @Index(name = "idx_sku_code", columnList = "sku_code")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProductSKU {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "sku_code", nullable = false, length = 100)
    private String skuCode;

    @Builder.Default
    @Convert(converter = JsonConverters.JsonMapConverter.class)
    @Column(columnDefinition = "TEXT")
    private Map<String, Object> attributes = new LinkedHashMap<>();

    /** 瑕嗙洊鍟嗗搧鍩虹浠凤紝null 鍒欎娇鐢ㄥ晢鍝佷环 */
    private Double price;

    @Builder.Default
    private Integer stock = 0;

    @Builder.Default
    @Column(length = 500)
    private String image = "";

    @Builder.Default
    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}