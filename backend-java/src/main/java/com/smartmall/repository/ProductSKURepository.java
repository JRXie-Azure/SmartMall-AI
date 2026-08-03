package com.smartmall.repository;

import com.smartmall.entity.ProductSKU;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ProductSKURepository extends JpaRepository<ProductSKU, Long> {

    List<ProductSKU> findByProductIdAndIsActiveTrue(Long productId);

    List<ProductSKU> findByProductId(Long productId);
}