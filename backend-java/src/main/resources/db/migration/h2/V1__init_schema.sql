-- SmartMall-AI 初始表结构 (H2, MODE=MySQL)
-- 与 mysql/V1__init_schema.sql 等价，差异仅在方言：
--   1. H2 不支持 CREATE TABLE 内联 KEY，索引拆成独立 CREATE INDEX
--   2. TEXT 用不限长 VARCHAR 代替，绕开 CLOB 绑定的坑
--   3. 无 ENGINE / CHARSET 子句

CREATE TABLE users (
    id              BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    avatar          VARCHAR(500)          DEFAULT '',
    phone           VARCHAR(20)           DEFAULT '',
    is_active       BOOLEAN               DEFAULT TRUE,
    created_at      TIMESTAMP             DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NULL
);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_username ON users (username);

CREATE TABLE categories (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    icon       VARCHAR(200) DEFAULT '',
    sort_order INT          DEFAULT 0,
    parent_id  BIGINT       NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE addresses (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT       NOT NULL,
    name       VARCHAR(100) NOT NULL,
    phone      VARCHAR(20)  NOT NULL,
    province   VARCHAR(50)  NOT NULL,
    city       VARCHAR(50)  NOT NULL,
    district   VARCHAR(50)  NOT NULL,
    detail     VARCHAR(500) NOT NULL,
    is_default BOOLEAN      DEFAULT FALSE,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_addr_user ON addresses (user_id);

CREATE TABLE products (
    id             BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(300) NOT NULL,
    description    VARCHAR,
    price          DOUBLE       NOT NULL,
    original_price DOUBLE       NULL,
    image          VARCHAR(500) DEFAULT '',
    images         VARCHAR,
    stock          INT          DEFAULT 0,
    sales          INT          DEFAULT 0,
    category_id    BIGINT       NULL,
    tags           VARCHAR,
    brand          VARCHAR(100) DEFAULT '',
    rating         DOUBLE       DEFAULT 5.0,
    is_recommend   BOOLEAN      DEFAULT FALSE,
    is_new         BOOLEAN      DEFAULT FALSE,
    is_sale        BOOLEAN      DEFAULT FALSE,
    is_active      BOOLEAN      DEFAULT TRUE,
    audit_status   VARCHAR(20)  DEFAULT 'approved',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NULL
);
CREATE INDEX idx_product_name ON products (name);
CREATE INDEX idx_product_category ON products (category_id);
CREATE INDEX idx_product_active_audit ON products (is_active, audit_status);

CREATE TABLE cart_items (
    id         BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT    NOT NULL,
    product_id BIGINT    NOT NULL,
    quantity   INT       NOT NULL DEFAULT 1,
    created_at TIMESTAMP          DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
CREATE INDEX idx_cart_user ON cart_items (user_id);

CREATE TABLE orders (
    id                BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id           BIGINT      NOT NULL,
    order_no          VARCHAR(64) NOT NULL UNIQUE,
    status            VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount      DOUBLE      NOT NULL,
    address_snapshot  VARCHAR     NOT NULL,
    note              VARCHAR,
    payment_method    VARCHAR(50)          DEFAULT '',
    paid_at           TIMESTAMP   NULL,
    shipped_at        TIMESTAMP   NULL,
    completed_at      TIMESTAMP   NULL,
    tracking_no       VARCHAR(100)         DEFAULT '',
    logistics_company VARCHAR(100)         DEFAULT '',
    created_at        TIMESTAMP            DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP   NULL
);
CREATE INDEX idx_order_user_status ON orders (user_id, status);
CREATE INDEX idx_order_created ON orders (created_at);
CREATE INDEX idx_order_no ON orders (order_no);

CREATE TABLE order_items (
    id            BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_id      BIGINT       NOT NULL,
    product_id    BIGINT       NOT NULL,
    product_name  VARCHAR(300) NOT NULL,
    product_image VARCHAR(500) DEFAULT '',
    price         DOUBLE       NOT NULL,
    quantity      INT          NOT NULL
);
CREATE INDEX idx_oi_order ON order_items (order_id);
CREATE INDEX idx_oi_product ON order_items (product_id);

CREATE TABLE reviews (
    id           BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT    NOT NULL,
    product_id   BIGINT    NOT NULL,
    order_id     BIGINT    NULL,
    rating       INT       NOT NULL,
    content      VARCHAR,
    images       VARCHAR,
    is_anonymous BOOLEAN   DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_review_product ON reviews (product_id);
CREATE INDEX idx_review_user ON reviews (user_id);

CREATE TABLE product_views (
    id         BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT    NOT NULL,
    product_id BIGINT    NOT NULL,
    view_count INT       DEFAULT 1,
    duration   INT       DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
CREATE INDEX idx_view_user ON product_views (user_id);
CREATE INDEX idx_view_product ON product_views (product_id);
CREATE UNIQUE INDEX idx_view_user_product ON product_views (user_id, product_id);

CREATE TABLE favorites (
    id         BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT    NOT NULL,
    product_id BIGINT    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_fav_user_product ON favorites (user_id, product_id);

CREATE TABLE chat_sessions (
    id                BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id        VARCHAR(64) NOT NULL UNIQUE,
    user_id           BIGINT      NULL,
    user_name         VARCHAR(100) DEFAULT '访客',
    status            VARCHAR(20)  DEFAULT 'active',
    assigned_agent_id BIGINT      NULL,
    summary           VARCHAR,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    closed_at         TIMESTAMP   NULL
);
CREATE INDEX idx_chat_session_sid ON chat_sessions (session_id);

CREATE TABLE chat_messages (
    id          BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id  BIGINT      NOT NULL,
    sender_type VARCHAR(20) NOT NULL,
    content     VARCHAR     NOT NULL,
    `metadata`  VARCHAR,
    created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chat_msg_session ON chat_messages (session_id);

CREATE TABLE search_histories (
    id           BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT       NULL,
    keyword      VARCHAR(500) NOT NULL,
    result_count INT          DEFAULT 0,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_search_user ON search_histories (user_id);
CREATE INDEX idx_search_keyword ON search_histories (keyword);
