package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/** 浏览记录。协同过滤的隐式反馈来源之一（权重 1.0） */
@Entity
@Table(name = "product_views", indexes = {
        @Index(name = "idx_view_user", columnList = "user_id"),
        @Index(name = "idx_view_product", columnList = "product_id"),
        @Index(name = "idx_view_user_product", columnList = "user_id,product_id", unique = true)
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProductView {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Builder.Default
    @Column(name = "view_count")
    private Integer viewCount = 1;

    /** 停留秒数 */
    @Builder.Default
    private Integer duration = 0;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
