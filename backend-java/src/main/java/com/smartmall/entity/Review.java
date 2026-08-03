package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/** 商品评价 */
@Entity
@Table(name = "reviews", indexes = {
        @Index(name = "idx_review_product", columnList = "product_id"),
        @Index(name = "idx_review_user", columnList = "user_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Review {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "order_id")
    private Long orderId;

    /** 1-5 星 */
    @Column(nullable = false)
    private Integer rating;

    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String content = "";

    @Builder.Default
    @Convert(converter = JsonConverters.StringListConverter.class)
    @Column(columnDefinition = "TEXT")
    private List<String> images = new ArrayList<>();

    @Builder.Default
    @Column(name = "is_anonymous")
    private Boolean isAnonymous = false;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
