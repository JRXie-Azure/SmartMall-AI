package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/** 搜索历史，用于热搜榜与个性化 */
@Entity
@Table(name = "search_histories", indexes = {
        @Index(name = "idx_search_user", columnList = "user_id"),
        @Index(name = "idx_search_keyword", columnList = "keyword")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SearchHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 允许为空 —— 未登录用户的搜索也记录 */
    @Column(name = "user_id")
    private Long userId;

    @Column(nullable = false, length = 500)
    private String keyword;

    @Builder.Default
    @Column(name = "result_count")
    private Integer resultCount = 0;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
