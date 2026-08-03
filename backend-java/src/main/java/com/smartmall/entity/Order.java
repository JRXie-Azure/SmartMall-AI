package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 订单。状态机: pending → paid → shipped → completed，另有 cancelled / refunded 分支 */
@Entity
@Table(name = "orders", indexes = {
        @Index(name = "idx_order_user_status", columnList = "user_id,status"),
        @Index(name = "idx_order_created", columnList = "created_at"),
        @Index(name = "idx_order_no", columnList = "order_no")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "order_no", nullable = false, unique = true, length = 64)
    private String orderNo;

    @Builder.Default
    @Column(nullable = false, length = 20)
    private String status = "pending";

    @Column(name = "total_amount", nullable = false)
    private Double totalAmount;

    /** 下单时的地址快照，避免地址被改动后历史订单失真 */
    @Builder.Default
    @Convert(converter = JsonConverters.JsonMapConverter.class)
    @Column(name = "address_snapshot", nullable = false, columnDefinition = "TEXT")
    private Map<String, Object> addressSnapshot = new LinkedHashMap<>();

    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String note = "";

    @Builder.Default
    @Column(name = "payment_method", length = 50)
    private String paymentMethod = "";

    @Column(name = "paid_at")
    private LocalDateTime paidAt;

    @Column(name = "shipped_at")
    private LocalDateTime shippedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Builder.Default
    @Column(name = "tracking_no", length = 100)
    private String trackingNo = "";

    @Builder.Default
    @Column(name = "logistics_company", length = 100)
    private String logisticsCompany = "";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    /**
     * 只读明细集合。OrderItem 把 order_id 建模成普通 Long（便于批量写入），
     * 所以这里不能用 mappedBy，改用只读 JoinColumn；写入统一走 OrderItemRepository。
     */
    @Builder.Default
    @OneToMany(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", insertable = false, updatable = false)
    @OrderBy("id ASC")
    private List<OrderItem> items = new ArrayList<>();
}
