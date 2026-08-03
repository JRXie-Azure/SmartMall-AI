-- SmartMall-AI 初始表结构 (MySQL 8)
-- 与原 Python SQLAlchemy models.py 1:1 对应，共 13 张表。
-- 价格统一 DOUBLE：刻意对齐 Python float，避免 JSON 从 799.0 变成 799.00 破坏前端。
-- 时间统一 DATETIME(6)：SQLite 存的是 6 位微秒，MySQL 默认 DATETIME 精度为 0 会四舍五入，
--   导致同一条记录在两套后端的 created_at 输出对不上，比对时误判为差异。

CREATE TABLE users (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    email           VARCHAR(255) NOT NULL,
    username        VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    avatar          VARCHAR(500)          DEFAULT '',
    phone           VARCHAR(20)           DEFAULT '',
    is_active       BOOLEAN               DEFAULT TRUE,
    created_at      DATETIME(6)              DEFAULT CURRENT_TIMESTAMP(6),
    updated_at      DATETIME(6)              NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_email (email),
    UNIQUE KEY uk_users_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE categories (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    icon       VARCHAR(200) DEFAULT '',
    sort_order INT          DEFAULT 0,
    parent_id  BIGINT       NULL,
    created_at DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE addresses (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    user_id    BIGINT       NOT NULL,
    name       VARCHAR(100) NOT NULL,
    phone      VARCHAR(20)  NOT NULL,
    province   VARCHAR(50)  NOT NULL,
    city       VARCHAR(50)  NOT NULL,
    district   VARCHAR(50)  NOT NULL,
    detail     VARCHAR(500) NOT NULL,
    is_default BOOLEAN      DEFAULT FALSE,
    created_at DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_addr_user (user_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE products (
    id             BIGINT       NOT NULL AUTO_INCREMENT,
    name           VARCHAR(300) NOT NULL,
    description    TEXT,
    price          DOUBLE       NOT NULL,
    original_price DOUBLE       NULL,
    image          VARCHAR(500) DEFAULT '',
    images         TEXT,
    stock          INT          DEFAULT 0,
    sales          INT          DEFAULT 0,
    category_id    BIGINT       NULL,
    tags           TEXT,
    brand          VARCHAR(100) DEFAULT '',
    rating         DOUBLE       DEFAULT 5.0,
    is_recommend   BOOLEAN      DEFAULT FALSE,
    is_new         BOOLEAN      DEFAULT FALSE,
    is_sale        BOOLEAN      DEFAULT FALSE,
    is_active      BOOLEAN      DEFAULT TRUE,
    audit_status   VARCHAR(20)  DEFAULT 'approved',
    created_at     DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    updated_at     DATETIME(6)     NULL,
    PRIMARY KEY (id),
    KEY idx_product_name (name),
    KEY idx_product_category (category_id),
    KEY idx_product_active_audit (is_active, audit_status)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE cart_items (
    id         BIGINT   NOT NULL AUTO_INCREMENT,
    user_id    BIGINT   NOT NULL,
    product_id BIGINT   NOT NULL,
    quantity   INT      NOT NULL DEFAULT 1,
    created_at DATETIME(6)          DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NULL,
    PRIMARY KEY (id),
    KEY idx_cart_user (user_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE orders (
    id                BIGINT      NOT NULL AUTO_INCREMENT,
    user_id           BIGINT      NOT NULL,
    order_no          VARCHAR(64) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount      DOUBLE      NOT NULL,
    address_snapshot  TEXT        NOT NULL,
    note              TEXT,
    payment_method    VARCHAR(50)          DEFAULT '',
    paid_at           DATETIME(6)    NULL,
    shipped_at        DATETIME(6)    NULL,
    completed_at      DATETIME(6)    NULL,
    tracking_no       VARCHAR(100)         DEFAULT '',
    logistics_company VARCHAR(100)         DEFAULT '',
    created_at        DATETIME(6)             DEFAULT CURRENT_TIMESTAMP(6),
    updated_at        DATETIME(6)    NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_order_no (order_no),
    KEY idx_order_user_status (user_id, status),
    KEY idx_order_created (created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE order_items (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    order_id      BIGINT       NOT NULL,
    product_id    BIGINT       NOT NULL,
    product_name  VARCHAR(300) NOT NULL,
    product_image VARCHAR(500) DEFAULT '',
    price         DOUBLE       NOT NULL,
    quantity      INT          NOT NULL,
    PRIMARY KEY (id),
    KEY idx_oi_order (order_id),
    KEY idx_oi_product (product_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE reviews (
    id           BIGINT   NOT NULL AUTO_INCREMENT,
    user_id      BIGINT   NOT NULL,
    product_id   BIGINT   NOT NULL,
    order_id     BIGINT   NULL,
    rating       INT      NOT NULL,
    content      TEXT,
    images       TEXT,
    is_anonymous BOOLEAN  DEFAULT FALSE,
    created_at   DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_review_product (product_id),
    KEY idx_review_user (user_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE product_views (
    id         BIGINT   NOT NULL AUTO_INCREMENT,
    user_id    BIGINT   NOT NULL,
    product_id BIGINT   NOT NULL,
    view_count INT      DEFAULT 1,
    duration   INT      DEFAULT 0,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NULL,
    PRIMARY KEY (id),
    KEY idx_view_user (user_id),
    KEY idx_view_product (product_id),
    UNIQUE KEY idx_view_user_product (user_id, product_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE favorites (
    id         BIGINT   NOT NULL AUTO_INCREMENT,
    user_id    BIGINT   NOT NULL,
    product_id BIGINT   NOT NULL,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY idx_fav_user_product (user_id, product_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE chat_sessions (
    id                BIGINT      NOT NULL AUTO_INCREMENT,
    session_id        VARCHAR(64) NOT NULL,
    user_id           BIGINT      NULL,
    user_name         VARCHAR(100) DEFAULT '访客',
    status            VARCHAR(20)  DEFAULT 'active',
    assigned_agent_id BIGINT      NULL,
    summary           TEXT,
    created_at        DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    closed_at         DATETIME(6)    NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_chat_session_sid (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE chat_messages (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    session_id  BIGINT      NOT NULL,
    sender_type VARCHAR(20) NOT NULL,
    content     TEXT        NOT NULL,
    `metadata`  TEXT,
    created_at  DATETIME(6)    DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_chat_msg_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE search_histories (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    user_id      BIGINT       NULL,
    keyword      VARCHAR(500) NOT NULL,
    result_count INT          DEFAULT 0,
    created_at   DATETIME(6)     DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_search_user (user_id),
    KEY idx_search_keyword (keyword)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
