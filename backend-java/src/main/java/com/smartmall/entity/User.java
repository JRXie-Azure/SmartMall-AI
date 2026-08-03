package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/** 用户表，含 RBAC 三角色: user / merchant / admin */
@Entity
@Table(name = "users", indexes = {
        @Index(name = "idx_users_email", columnList = "email"),
        @Index(name = "idx_users_username", columnList = "username")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(nullable = false, unique = true, length = 100)
    private String username;

    /** bcrypt 哈希。沿用 Python passlib 生成的 $2b$ 串，Spring 的 BCryptPasswordEncoder 可直接校验 */
    @Column(name = "hashed_password", nullable = false, length = 255)
    private String hashedPassword;

    @Builder.Default
    @Column(nullable = false, length = 20)
    private String role = "user";

    @Builder.Default
    @Column(length = 500)
    private String avatar = "";

    @Builder.Default
    @Column(length = 20)
    private String phone = "";

    @Builder.Default
    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
