package com.smartmall.repository;

import com.smartmall.entity.Review;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReviewRepository extends JpaRepository<Review, Long> {

    List<Review> findByProductIdOrderByCreatedAtDescIdAsc(Long productId);

    List<Review> findByProductId(Long productId);
}
