package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * 鐢ㄦ埛棰嗗彇鐨勪紭鎯犲埜銆? *
 * <p>瀵瑰簲 Python models.py 涓殑 UserCoupon銆? */
@Entity
@Table(name = "user_coupons", indexes = {
        @Index(name = "idx_user_coupon", columnList = "user_id, coupon_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserCoupon {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "coupon_id", nullable = false)
    private Long couponId;

    @Builder.Default
    @Column(name = "used_count")
    private Integer usedCount = 0;

    @Builder.Default
    @Column(name = "is_used")
    private Boolean isUsed = false;

    @Column(name = "used_at")
    private LocalDateTime usedAt;

    @Column(name = "order_id")
    private Long orderId;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "coupon_id", insertable = false, updatable = false)
    private Coupon coupon;
}