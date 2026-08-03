package com.smartmall.repository;

import com.smartmall.entity.UserCoupon;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface UserCouponRepository extends JpaRepository<UserCoupon, Long> {

    Optional<UserCoupon> findByUserIdAndCouponId(Long userId, Long couponId);

    List<UserCoupon> findByUserIdAndIsUsedFalse(Long userId);

    long countByUserIdAndCouponId(Long userId, Long couponId);
}