package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;

/** 订单明细。商品名/图/价格均为下单时快照 */
@Entity
@Table(name = "order_items", indexes = {
        @Index(name = "idx_oi_order", columnList = "order_id"),
        @Index(name = "idx_oi_product", columnList = "product_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "product_name", nullable = false, length = 300)
    private String productName;

    @Builder.Default
    @Column(name = "product_image", length = 500)
    private String productImage = "";

    @Column(nullable = false)
    private Double price;

    @Column(nullable = false)
    private Integer quantity;
}
