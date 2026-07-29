"""add sku coupon marketing banner config tables

Revision ID: a1b2c3d4e5f6
Revises: 9604473bed6f
Create Date: 2026-07-27 22:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9604473bed6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 商品 SKU
    op.create_table('product_skus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('sku_code', sa.String(length=100), nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('image', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_skus_sku_code', 'product_skus', ['sku_code'], unique=False)

    # 商品规格模板
    op.create_table('product_variants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 优惠券
    op.create_table('coupons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_type', sa.String(length=20), nullable=True),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('min_order_amount', sa.Float(), nullable=True),
        sa.Column('max_discount', sa.Float(), nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_limit', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=True),
        sa.Column('per_user_limit', sa.Integer(), nullable=True),
        sa.Column('applicable_products', sa.JSON(), nullable=True),
        sa.Column('applicable_categories', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_coupons_code', 'coupons', ['code'], unique=True)

    # 用户优惠券
    op.create_table('user_coupons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('coupon_id', sa.Integer(), nullable=False),
        sa.Column('used_count', sa.Integer(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_coupon', 'user_coupons', ['user_id', 'coupon_id'], unique=False)

    # 营销活动
    op.create_table('marketing_campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('campaign_type', sa.String(length=30), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('banner_image', sa.String(length=500), nullable=True),
        sa.Column('discount_value', sa.Float(), nullable=True),
        sa.Column('min_order_amount', sa.Float(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('applicable_products', sa.JSON(), nullable=True),
        sa.Column('applicable_categories', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Banner 轮播图
    op.create_table('banners',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('image', sa.String(length=500), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 系统配置
    op.create_table('site_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_site_configs_config_key', 'site_configs', ['config_key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_site_configs_config_key', table_name='site_configs')
    op.drop_table('site_configs')
    op.drop_table('banners')
    op.drop_table('marketing_campaigns')
    op.drop_index('idx_user_coupon', table_name='user_coupons')
    op.drop_table('user_coupons')
    op.drop_index('ix_coupons_code', table_name='coupons')
    op.drop_table('coupons')
    op.drop_table('product_variants')
    op.drop_index('ix_product_skus_sku_code', table_name='product_skus')
    op.drop_table('product_skus')
