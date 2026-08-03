package com.smartmall.repository;

import com.smartmall.entity.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    boolean existsByEmailOrUsername(String email, String username);

    boolean existsByEmailAndIdNot(String email, Long id);

    Page<User> findAllByOrderByCreatedAtDescIdAsc(Pageable pageable);

    Page<User> findByRoleOrderByCreatedAtDescIdAsc(String role, Pageable pageable);

    /** 用户增长曲线: 按天聚合注册量。用原生 SQL 以兼容 MySQL/H2 的 DATE() 函数 */
    @Query(value = "SELECT DATE(created_at) AS d, COUNT(*) AS c FROM users " +
            "WHERE created_at >= :since GROUP BY DATE(created_at) ORDER BY d",
            nativeQuery = true)
    List<Object[]> countGroupByDaySince(@Param("since") LocalDateTime since);
}
