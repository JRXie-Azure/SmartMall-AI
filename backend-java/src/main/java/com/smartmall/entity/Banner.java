package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * 棣栭〉杞挱鍥俱€? *
 * <p>瀵瑰簲 Python models.py 涓殑 Banner銆? */
@Entity
@Table(name = "banners")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Banner {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Builder.Default
    @Column(length = 200)
    private String title = "";

    @Column(nullable = false, length = 500)
    private String image;

    @Builder.Default
    @Column(length = 500)
    private String link = "";

    @Builder.Default
    @Column(name = "sort_order")
    private Integer sortOrder = 0;

    @Builder.Default
    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}