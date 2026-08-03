package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 鍟嗗搧瑙勬牸妯℃澘 (濡? 棰滆壊銆佸昂瀵?銆? *
 * <p>瀵瑰簲 Python models.py 涓殑 ProductVariant锛宱ptions 瀛樺偍 ["绾㈣壊", "钃濊壊"] 绛夐€夐」鍒楄〃銆? */
@Entity
@Table(name = "product_variants")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProductVariant {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(nullable = false, length = 50)
    private String name;

    @Builder.Default
    @Convert(converter = JsonConverters.StringListConverter.class)
    @Column(columnDefinition = "TEXT")
    private List<String> options = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}