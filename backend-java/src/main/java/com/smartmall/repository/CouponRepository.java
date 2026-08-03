package com.smartmall.repository;

import com.smartmall.entity.Coupon;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CouponRepository extends JpaRepository<Coupon, Long> {

    Coupon findByCodeAndIsActiveTrue(String code);

    List<Coupon> findByIsActiveTrue();
}