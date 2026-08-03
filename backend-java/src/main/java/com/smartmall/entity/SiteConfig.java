package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/**
 * 绯荤粺閰嶇疆 (閿€煎)銆? *
 * <p>瀵瑰簲 Python models.py 涓殑 SiteConfig銆? */
@Entity
@Table(name = "site_configs", indexes = {
        @Index(name = "idx_config_key", columnList = "config_key")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SiteConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "config_key", nullable = false, unique = true, length = 100)
    private String configKey;

    @Builder.Default
    @Column(name = "config_value", columnDefinition = "TEXT")
    private String configValue = "";

    @Builder.Default
    @Column(length = 500)
    private String description = "";

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}