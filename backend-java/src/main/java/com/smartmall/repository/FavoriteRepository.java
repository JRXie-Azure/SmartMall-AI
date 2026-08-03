package com.smartmall.repository;

import com.smartmall.entity.Favorite;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface FavoriteRepository extends JpaRepository<Favorite, Long> {

    Optional<Favorite> findByUserIdAndProductId(Long userId, Long productId);

    List<Favorite> findByUserIdOrderByCreatedAtDescIdAsc(Long userId);

    /** 协同过滤矩阵原料: [userId, productId] */
    @Query("SELECT f.userId, f.productId FROM Favorite f")
    List<Object[]> findAllFavoritePairs();
}
