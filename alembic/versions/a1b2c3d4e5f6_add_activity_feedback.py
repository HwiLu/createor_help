"""add activity & feedback modules

Revision ID: a1b2c3d4e5f6
Revises: e0e100d39ac1
Create Date: 2026-10-12 00:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e0e100d39ac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> datetime:
    return datetime.utcnow()


def upgrade() -> None:
    # 活动平台字典
    op.create_table(
        'activity_platforms',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_platforms_code'), 'activity_platforms', ['code'], unique=True)

    # 活动类型字典
    op.create_table(
        'activity_types',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_types_code'), 'activity_types', ['code'], unique=True)

    # 活动主表
    op.create_table(
        'activities',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('cover_image_key', sa.String(length=256), nullable=False),
        sa.Column('platform_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('activity_type_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('summary', sa.String(length=300), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('start_at', sa.DateTime(), nullable=True),
        sa.Column('end_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('featured_sort', sa.Integer(), nullable=False),
        sa.Column('display_sort', sa.Integer(), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('risk_notice', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['activity_type_id'], ['activity_types.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['activity_platforms.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activities_activity_type_id'), 'activities', ['activity_type_id'], unique=False)
    op.create_index(op.f('ix_activities_created_at'), 'activities', ['created_at'], unique=False)
    op.create_index(op.f('ix_activities_display_sort'), 'activities', ['display_sort'], unique=False)
    op.create_index(op.f('ix_activities_is_featured'), 'activities', ['is_featured'], unique=False)
    op.create_index(op.f('ix_activities_platform_id'), 'activities', ['platform_id'], unique=False)
    op.create_index(op.f('ix_activities_status'), 'activities', ['status'], unique=False)

    # 活动参与入口
    op.create_table(
        'activity_entries',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('entry_type', sa.String(length=16), nullable=False),
        sa.Column('qr_image_key', sa.String(length=256), nullable=True),
        sa.Column('target_url', sa.String(length=512), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_entries_activity_id'), 'activity_entries', ['activity_id'], unique=False)

    # 活动评论
    op.create_table(
        'activity_comments',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('parent_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('reply_to_user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.ForeignKeyConstraint(['reply_to_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_comments_activity_id'), 'activity_comments', ['activity_id'], unique=False)
    op.create_index(op.f('ix_activity_comments_parent_id'), 'activity_comments', ['parent_id'], unique=False)
    op.create_index(op.f('ix_activity_comments_status'), 'activity_comments', ['status'], unique=False)
    op.create_index(op.f('ix_activity_comments_user_id'), 'activity_comments', ['user_id'], unique=False)

    # 活动举报
    op.create_table(
        'activity_reports',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('comment_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('reporter_user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('reason', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('handled_by', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.ForeignKeyConstraint(['comment_id'], ['activity_comments.id'], ),
        sa.ForeignKeyConstraint(['handled_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reporter_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_reports_activity_id'), 'activity_reports', ['activity_id'], unique=False)
    op.create_index(op.f('ix_activity_reports_comment_id'), 'activity_reports', ['comment_id'], unique=False)
    op.create_index(op.f('ix_activity_reports_reporter_user_id'), 'activity_reports', ['reporter_user_id'], unique=False)
    op.create_index(op.f('ix_activity_reports_status'), 'activity_reports', ['status'], unique=False)

    # 反馈分类字典
    op.create_table(
        'feedback_categories',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_categories_code'), 'feedback_categories', ['code'], unique=True)

    # 反馈主表
    op.create_table(
        'feedbacks',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('category_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('related_url', sa.String(length=512), nullable=True),
        sa.Column('contact_info', sa.String(length=256), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('handled_by', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('handled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['feedback_categories.id'], ),
        sa.ForeignKeyConstraint(['handled_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedbacks_category_id'), 'feedbacks', ['category_id'], unique=False)
    op.create_index(op.f('ix_feedbacks_created_at'), 'feedbacks', ['created_at'], unique=False)
    op.create_index(op.f('ix_feedbacks_status'), 'feedbacks', ['status'], unique=False)
    op.create_index(op.f('ix_feedbacks_user_id'), 'feedbacks', ['user_id'], unique=False)

    # 邮件投递日志
    op.create_table(
        'email_delivery_logs',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('feedback_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('recipient_email', sa.String(length=256), nullable=False),
        sa.Column('subject', sa.String(length=256), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedbacks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_delivery_logs_feedback_id'), 'email_delivery_logs', ['feedback_id'], unique=False)
    op.create_index(op.f('ix_email_delivery_logs_status'), 'email_delivery_logs', ['status'], unique=False)

    # 系统配置
    op.create_table(
        'system_settings',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # 初始化默认字典数据（可配置字典，后续可在后台维护）
    _seed_dictionaries()


def _seed_dictionaries() -> None:
    now = _now()

    platforms = sa.table(
        'activity_platforms',
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        platforms,
        [
            {'name': '拼多多', 'code': 'PDD', 'sort_order': 1, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '支付宝', 'code': 'ALIPAY', 'sort_order': 2, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '招商银行', 'code': 'CMB', 'sort_order': 3, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '京东', 'code': 'JD', 'sort_order': 4, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '淘宝/天猫', 'code': 'TAOBAO', 'sort_order': 5, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '抖音', 'code': 'DOUYIN', 'sort_order': 6, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '微信', 'code': 'WECHAT', 'sort_order': 7, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '其他平台', 'code': 'OTHER', 'sort_order': 8, 'is_active': True, 'created_at': now, 'updated_at': now},
        ],
    )

    types = sa.table(
        'activity_types',
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        types,
        [
            {'name': '砍价助力', 'code': 'BARGAIN', 'sort_order': 1, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '邀请好友', 'code': 'INVITE', 'sort_order': 2, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '集卡活动', 'code': 'CARD_COLLECTION', 'sort_order': 3, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '组队活动', 'code': 'TEAM', 'sort_order': 4, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '抽奖活动', 'code': 'LOTTERY', 'sort_order': 5, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '限时福利', 'code': 'LIMITED_OFFER', 'sort_order': 6, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '其他活动', 'code': 'OTHER', 'sort_order': 7, 'is_active': True, 'created_at': now, 'updated_at': now},
        ],
    )

    categories = sa.table(
        'feedback_categories',
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        categories,
        [
            {'name': '功能意见', 'code': 'FEATURE', 'sort_order': 1, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '新活动提交', 'code': 'NEW_ACTIVITY', 'sort_order': 2, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '页面体验问题', 'code': 'UX', 'sort_order': 3, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': 'Bug / 错误反馈', 'code': 'BUG', 'sort_order': 4, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '内容纠错或失效活动', 'code': 'CORRECTION', 'sort_order': 5, 'is_active': True, 'created_at': now, 'updated_at': now},
            {'name': '其他建议', 'code': 'OTHER', 'sort_order': 6, 'is_active': True, 'created_at': now, 'updated_at': now},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_table('system_settings')
    op.drop_index(op.f('ix_email_delivery_logs_status'), table_name='email_delivery_logs')
    op.drop_index(op.f('ix_email_delivery_logs_feedback_id'), table_name='email_delivery_logs')
    op.drop_table('email_delivery_logs')
    op.drop_index(op.f('ix_feedbacks_user_id'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_status'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_created_at'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_category_id'), table_name='feedbacks')
    op.drop_table('feedbacks')
    op.drop_index(op.f('ix_feedback_categories_code'), table_name='feedback_categories')
    op.drop_table('feedback_categories')
    op.drop_index(op.f('ix_activity_reports_status'), table_name='activity_reports')
    op.drop_index(op.f('ix_activity_reports_reporter_user_id'), table_name='activity_reports')
    op.drop_index(op.f('ix_activity_reports_comment_id'), table_name='activity_reports')
    op.drop_index(op.f('ix_activity_reports_activity_id'), table_name='activity_reports')
    op.drop_table('activity_reports')
    op.drop_index(op.f('ix_activity_comments_user_id'), table_name='activity_comments')
    op.drop_index(op.f('ix_activity_comments_status'), table_name='activity_comments')
    op.drop_index(op.f('ix_activity_comments_parent_id'), table_name='activity_comments')
    op.drop_index(op.f('ix_activity_comments_activity_id'), table_name='activity_comments')
    op.drop_table('activity_comments')
    op.drop_index(op.f('ix_activity_entries_activity_id'), table_name='activity_entries')
    op.drop_table('activity_entries')
    op.drop_index(op.f('ix_activities_status'), table_name='activities')
    op.drop_index(op.f('ix_activities_platform_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_is_featured'), table_name='activities')
    op.drop_index(op.f('ix_activities_display_sort'), table_name='activities')
    op.drop_index(op.f('ix_activities_created_at'), table_name='activities')
    op.drop_index(op.f('ix_activities_activity_type_id'), table_name='activities')
    op.drop_table('activities')
    op.drop_index(op.f('ix_activity_types_code'), table_name='activity_types')
    op.drop_table('activity_types')
    op.drop_index(op.f('ix_activity_platforms_code'), table_name='activity_platforms')
    op.drop_table('activity_platforms')
