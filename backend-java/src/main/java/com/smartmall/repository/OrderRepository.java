package com.smartmall.repository;

import com.smartmall.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 注意所有「按创建时间倒序」的方法都额外带了 IdDesc 兜底，这一点与其它 Repository 相反。
 *
 * <p>原因在 SQLite 的执行计划：orders 表建了 idx_order_created(created_at) 索引，
 * ORDER BY created_at DESC 会走索引反向扫描，索引项按 (created_at, rowid) 升序存放，
 * 反着读出来同一时间戳的行就是 rowid 降序。其余表没有 created_at 索引，走
 * TEMP B-TREE 稳定排序，相同时间戳保持 rowid 升序 —— 所以那些地方用的是 IdAsc。
 */
public interface OrderRepository extends JpaRepository<Order, Long> {

    Page<Order> findByUserIdOrderByCreatedAtDescIdDesc(Long userId, Pageable pageable);

    Page<Order> findByUserIdAndStatusOrderByCreatedAtDescIdDesc(Long userId, String status, Pageable pageable);

    Optional<Order> findByIdAndUserId(Long id, Long userId);

    Optional<Order> findByOrderNo(String orderNo);

    Page<Order> findAllByOrderByCreatedAtDescIdDesc(Pageable pageable);

    Page<Order> findByStatusOrderByCreatedAtDescIdDesc(String status, Pageable pageable);

    /** 总销售额: 只统计已付款及之后的状态，与 Python 版口径一致 */
    @Query("SELECT COALESCE(SUM(o.totalAmount), 0) FROM Order o " +
            "WHERE o.status IN ('paid', 'shipped', 'completed')")
    Double sumPaidAmount();

    /**
     * 管理后台总销售额: 排除 cancelled，其余状态全算（含 pending / refunded）。
     * 口径刻意与 {@link #sumPaidAmount()} 不同 —— Python 版 admin.py 用的就是 status != 'cancelled'。
     */
    @Query("SELECT COALESCE(SUM(o.totalAmount), 0) FROM Order o WHERE o.status <> 'cancelled'")
    Double sumAmountExcludingCancelled();

    /** 订单状态分布: [status, count] */
    @Query("SELECT o.status, COUNT(o) FROM Order o GROUP BY o.status")
    List<Object[]> countGroupByStatus();

    /** 销售趋势（管理后台口径）: [date, sumAmount, orderCount]，金额排除 cancelled，单量不排除 */
    @Query(value = "SELECT DATE(created_at) AS d, " +
            "COALESCE(SUM(CASE WHEN status <> 'cancelled' THEN total_amount ELSE 0 END), 0) AS s, " +
            "COUNT(*) AS c " +
            "FROM orders WHERE created_at >= :since AND created_at < :until " +
            "GROUP BY DATE(created_at) ORDER BY d", nativeQuery = true)
    List<Object[]> salesTrendBetween(@Param("since") LocalDateTime since, @Param("until") LocalDateTime until);

    /** 销售趋势: [date, sum] 按天聚合 */
    @Query(value = "SELECT DATE(created_at) AS d, COALESCE(SUM(total_amount), 0) AS s FROM orders " +
            "WHERE created_at >= :since AND status IN ('paid','shipped','completed') " +
            "GROUP BY DATE(created_at) ORDER BY d", nativeQuery = true)
    List<Object[]> sumAmountGroupByDaySince(@Param("since") LocalDateTime since);

    /** 协同过滤: 用户购买过的商品 id（购买权重 5.0） */
    @Query("SELECT DISTINCT oi.productId FROM Order o JOIN OrderItem oi ON oi.orderId = o.id " +
            "WHERE o.userId = :userId AND o.status IN ('paid','shipped','completed')")
    List<Long> findPurchasedProductIds(@Param("userId") Long userId);

    /** 协同过滤全量行为矩阵所需: [userId, productId] */
    @Query("SELECT o.userId, oi.productId FROM Order o JOIN OrderItem oi ON oi.orderId = o.id " +
            "WHERE o.status IN ('paid','shipped','completed')")
    List<Object[]> findAllPurchasePairs();

    /**
     * 协同过滤真实口径: 每条 order_item 出一行（不去重），只排除 cancelled。
     * 与 Python recommendation_service.collaborative_filtering 完全一致：
     * 同一商品在多个订单里出现就会累加多次 +5 权重。
     */
    @Query("SELECT o.userId, oi.productId FROM Order o JOIN OrderItem oi ON oi.orderId = o.id " +
            "WHERE o.status <> 'cancelled'")
    List<Object[]> findAllOrderItemPairsExcludingCancelled();
}
