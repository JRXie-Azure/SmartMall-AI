-- SmartMall-AI MySQL 初始化
-- 用法: mysql -u root -p < mysql_init.sql

CREATE DATABASE IF NOT EXISTS smartmall
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE smartmall;

-- 表结构由 Alembic 自动创建:
--   python migrate_prod.py migrate
--   python migrate_prod.py seed
