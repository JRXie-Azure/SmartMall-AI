package com.smartmall.repository;

import com.smartmall.entity.Address;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AddressRepository extends JpaRepository<Address, Long> {

    List<Address> findByUserIdOrderByIsDefaultDescIdDesc(Long userId);

    Optional<Address> findByIdAndUserId(Long id, Long userId);

    Optional<Address> findFirstByUserIdAndIsDefaultTrue(Long userId);

    Optional<Address> findFirstByUserIdOrderByIdAsc(Long userId);
}
