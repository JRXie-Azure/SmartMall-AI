-- SmartMall-AI 琛ュ厖琛ㄧ粨鏋?(MySQL 8)
-- 鏂板 7 寮犺〃: product_skus / product_variants / coupons / user_coupons / marketing_campaigns / banners / site_configs

CREATE TABLE product_skus (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    product_id BIGINT       NOT NULL,
    sku_code   VARCHAR(100) NOT NULL,
    attributes TEXT,
    price      DOUBLE       NULL,
    stock      INT          DEFAULT 0,
    image      VARCHAR(500) DEFAULT '',
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_sku_product (product_id),
    KEY idx_sku_code (sku_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE product_variants (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    product_id BIGINT      NOT NULL,
    name       VARCHAR(50) NOT NULL,
    options    TEXT,
    created_at DATETIME(6)    DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE coupons (
    id                   BIGINT       NOT NULL AUTO_INCREMENT,
    code                 VARCHAR(50)  NOT NULL,
    name                 VARCHAR(100) NOT NULL,
    description          TEXT,
    discount_type        VARCHAR(20)  DEFAULT 'fixed',
    discount_value       DOUBLE       NOT NULL,
    min_order_amount     DOUBLE       DEFAULT 0,
    max_discount         DOUBLE       NULL,
    valid_from           DATETIME(6)  NULL,
    valid_until          DATETIME(6)  NULL,
    total_limit          INT          DEFAULT 0,
    used_count           INT          DEFAULT 0,
    per_user_limit       INT          DEFAULT 1,
    applicable_products  TEXT,
    applicable_categories TEXT,
    is_active            BOOLEAN      DEFAULT TRUE,
    created_at           DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_coupon_code (code),
    KEY idx_coupon_code (code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE user_coupons (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    user_id    BIGINT      NOT NULL,
    coupon_id  BIGINT      NOT NULL,
    used_count INT         DEFAULT 0,
    is_used    BOOLEAN     DEFAULT FALSE,
    used_at    DATETIME(6) NULL,
    order_id   BIGINT      NULL,
    created_at DATETIME(6)    DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_user_coupon (user_id, coupon_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE marketing_campaigns (
    id                   BIGINT       NOT NULL AUTO_INCREMENT,
    name                 VARCHAR(200) NOT NULL,
    campaign_type        VARCHAR(30)  DEFAULT 'discount',
    description          TEXT,
    banner_image         VARCHAR(500) DEFAULT '',
    discount_value       DOUBLE       DEFAULT 0,
    min_order_amount     DOUBLE       DEFAULT 0,
    start_time           DATETIME(6)  NOT NULL,
    end_time             DATETIME(6)  NOT NULL,
    applicable_products  TEXT,
    applicable_categories TEXT,
    is_active            BOOLEAN      DEFAULT TRUE,
    created_at           DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE banners (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    title      VARCHAR(200) DEFAULT '',
    image      VARCHAR(500) NOT NULL,
    link       VARCHAR(500) DEFAULT '',
    sort_order INT          DEFAULT 0,
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE site_configs (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    config_key   VARCHAR(100) NOT NULL,
    config_value TEXT,
    description  VARCHAR(500) DEFAULT '',
    updated_at   DATETIME(6)  NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_config_key (config_key),
    KEY idx_config_key (config_key)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;