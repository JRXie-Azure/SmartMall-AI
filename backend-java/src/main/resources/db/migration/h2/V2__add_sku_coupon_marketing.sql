-- SmartMall-AI 琛ュ厖琛ㄧ粨鏋?(H2, MODE=MySQL)
-- 鏂板 7 寮犺〃: product_skus / product_variants / coupons / user_coupons / marketing_campaigns / banners / site_configs
-- H2 鏂瑰樊寮? VARCHAR 浠ｆ浛 TEXT锛孋REATE INDEX 浠ｆ浛鍐呰仈 KEY锛屾棤 ENGINE/CHARSET

CREATE TABLE product_skus (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT       NOT NULL,
    sku_code   VARCHAR(100) NOT NULL,
    attributes VARCHAR,
    price      DOUBLE       NULL,
    stock      INT          DEFAULT 0,
    image      VARCHAR(500) DEFAULT '',
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sku_product ON product_skus (product_id);
CREATE INDEX idx_sku_code ON product_skus (sku_code);

CREATE TABLE product_variants (
    id         BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT      NOT NULL,
    name       VARCHAR(50) NOT NULL,
    options    VARCHAR,
    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE coupons (
    id                    BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code                  VARCHAR(50)  NOT NULL,
    name                  VARCHAR(100) NOT NULL,
    description           VARCHAR,
    discount_type         VARCHAR(20)  DEFAULT 'fixed',
    discount_value        DOUBLE       NOT NULL,
    min_order_amount      DOUBLE       DEFAULT 0,
    max_discount          DOUBLE       NULL,
    valid_from            TIMESTAMP    NULL,
    valid_until           TIMESTAMP    NULL,
    total_limit           INT          DEFAULT 0,
    used_count            INT          DEFAULT 0,
    per_user_limit        INT          DEFAULT 1,
    applicable_products   VARCHAR,
    applicable_categories VARCHAR,
    is_active             BOOLEAN      DEFAULT TRUE,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uk_coupon_code ON coupons (code);
CREATE INDEX idx_coupon_code ON coupons (code);

CREATE TABLE user_coupons (
    id         BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT    NOT NULL,
    coupon_id  BIGINT    NOT NULL,
    used_count INT       DEFAULT 0,
    is_used    BOOLEAN   DEFAULT FALSE,
    used_at    TIMESTAMP NULL,
    order_id   BIGINT    NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_coupon ON user_coupons (user_id, coupon_id);

CREATE TABLE marketing_campaigns (
    id                    BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name                  VARCHAR(200) NOT NULL,
    campaign_type         VARCHAR(30)  DEFAULT 'discount',
    description           VARCHAR,
    banner_image          VARCHAR(500) DEFAULT '',
    discount_value        DOUBLE       DEFAULT 0,
    min_order_amount      DOUBLE       DEFAULT 0,
    start_time            TIMESTAMP    NOT NULL,
    end_time              TIMESTAMP    NOT NULL,
    applicable_products   VARCHAR,
    applicable_categories VARCHAR,
    is_active             BOOLEAN      DEFAULT TRUE,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE banners (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title      VARCHAR(200) DEFAULT '',
    image      VARCHAR(500) NOT NULL,
    link       VARCHAR(500) DEFAULT '',
    sort_order INT          DEFAULT 0,
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE site_configs (
    id           BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    config_key   VARCHAR(100) NOT NULL,
    config_value VARCHAR,
    description  VARCHAR(500) DEFAULT '',
    updated_at   TIMESTAMP    NULL
);
CREATE UNIQUE INDEX uk_config_key ON site_configs (config_key);
CREATE INDEX idx_config_key ON site_configs (config_key);