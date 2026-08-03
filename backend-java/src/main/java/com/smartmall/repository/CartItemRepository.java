package com.smartmall.repository;

import com.smartmall.entity.CartItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CartItemRepository extends JpaRepository<CartItem, Long> {

    List<CartItem> findByUserIdOrderByIdAsc(Long userId);

    Optional<CartItem> findByUserIdAndProductId(Long userId, Long productId);

    Optional<CartItem> findByIdAndUserId(Long id, Long userId);

    long countByUserId(Long userId);

    void deleteByUserId(Long userId);
}
