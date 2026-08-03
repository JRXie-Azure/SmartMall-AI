package com.smartmall.repository;

import com.smartmall.entity.ProductView;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface ProductViewRepository extends JpaRepository<ProductView, Long> {

    Optional<ProductView> findByUserIdAndProductId(Long userId, Long productId);

    List<ProductView> findByUserId(Long userId);

    /** 内容推荐: 最近浏览的 10 个商品 */
    List<ProductView> findTop10ByUserIdOrderByUpdatedAtDesc(Long userId);

    /** 协同过滤矩阵原料: [userId, productId, viewCount] */
    @Query("SELECT v.userId, v.productId, v.viewCount FROM ProductView v")
    List<Object[]> findAllViewTriples();
}
