"""add views likes reviews credit

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bigint():
    return sa.BigInteger().with_variant(sa.Integer(), 'sqlite')


def upgrade() -> None:
    # 浏览量 / 信用分
    op.add_column('posts', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('activities', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('credit_score', sa.Integer(), nullable=False, server_default='100'))

    # 点赞
    op.create_table(
        'likes',
        sa.Column('id', _bigint(), primary_key=True, autoincrement=True),
        sa.Column('user_id', _bigint(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('target_type', sa.String(length=16), nullable=False),
        sa.Column('target_id', _bigint(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_likes_user_target'),
    )
    op.create_index(op.f('ix_likes_user_id'), 'likes', ['user_id'], unique=False)
    op.create_index(op.f('ix_likes_target_type'), 'likes', ['target_type'], unique=False)
    op.create_index(op.f('ix_likes_target_id'), 'likes', ['target_id'], unique=False)

    # 用户评价
    op.create_table(
        'reviews',
        sa.Column('id', _bigint(), primary_key=True, autoincrement=True),
        sa.Column('reviewer_id', _bigint(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewee_id', _bigint(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('apply_comment_id', _bigint(), sa.ForeignKey('comments.id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('reviewer_id', 'apply_comment_id', name='uq_reviews_reviewer_apply'),
    )
    op.create_index(op.f('ix_reviews_reviewer_id'), 'reviews', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_reviews_reviewee_id'), 'reviews', ['reviewee_id'], unique=False)
    op.create_index(op.f('ix_reviews_apply_comment_id'), 'reviews', ['apply_comment_id'], unique=False)

    # 信用分流水
    op.create_table(
        'credit_logs',
        sa.Column('id', _bigint(), primary_key=True, autoincrement=True),
        sa.Column('user_id', _bigint(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('change', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=True),
        sa.Column('entity_id', _bigint(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', 'reason', name='uq_credit_log_idempotent'),
    )
    op.create_index(op.f('ix_credit_logs_user_id'), 'credit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_credit_logs_user_id'), table_name='credit_logs')
    op.drop_table('credit_logs')
    op.drop_index(op.f('ix_reviews_apply_comment_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_reviewee_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_reviewer_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_likes_target_id'), table_name='likes')
    op.drop_index(op.f('ix_likes_target_type'), table_name='likes')
    op.drop_index(op.f('ix_likes_user_id'), table_name='likes')
    op.drop_table('likes')
    op.drop_column('users', 'credit_score')
    op.drop_column('activities', 'view_count')
    op.drop_column('posts', 'view_count')
