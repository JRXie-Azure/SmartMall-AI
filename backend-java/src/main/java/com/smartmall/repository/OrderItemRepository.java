package com.smartmall.repository;

import com.smartmall.entity.OrderItem;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.Collection;
import java.util.List;

public interface OrderItemRepository extends JpaRepository<OrderItem, Long> {

    List<OrderItem> findByOrderIdOrderByIdAsc(Long orderId);

    List<OrderItem> findByOrderIdInOrderByIdAsc(Collection<Long> orderIds);

    /** 热销 TOP N: [productName, totalSold]，销量并列时按 product id 升序（对齐 SQLite 分组输出顺序） */
    @Query("SELECT p.name, SUM(oi.quantity) AS q FROM OrderItem oi JOIN Product p ON p.id = oi.productId " +
            "GROUP BY p.id, p.name ORDER BY q DESC, p.id ASC")
    List<Object[]> findTopSoldProducts(Pageable pageable);

    /** AI 转化率分子: 含推荐位商品的订单数（去重） */
    @Query("SELECT COUNT(DISTINCT oi.orderId) FROM OrderItem oi JOIN Product p ON p.id = oi.productId " +
            "WHERE p.isRecommend = true")
    long countDistinctOrdersWithRecommendedProduct();
}
