"""add comment image and mutual fields

Revision ID: d9e0f1a2b3c4
Revises: c3d4e5f6a7b8
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column('comments', sa.Column('parent_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    op.add_column('comments', sa.Column('image_key', sa.String(length=255), nullable=True))
    op.add_column('comments', sa.Column('comment_type', sa.String(length=24), nullable=False, server_default='COMMENT'))
    op.create_index(op.f('ix_comments_parent_id'), 'comments', ['parent_id'], unique=False)
    op.create_index(op.f('ix_comments_comment_type'), 'comments', ['comment_type'], unique=False)
    # SQLite 不支持 ALTER TABLE 增加约束，跳过自引用外键（本地开发不强制外键）
    if bind.dialect.name != 'sqlite':
        op.create_foreign_key('fk_comments_parent_id', 'comments', 'comments', ['parent_id'], ['id'])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.drop_constraint('fk_comments_parent_id', 'comments', type_='foreignkey')
    op.drop_index(op.f('ix_comments_comment_type'), table_name='comments')
    op.drop_index(op.f('ix_comments_parent_id'), table_name='comments')
    op.drop_column('comments', 'comment_type')
    op.drop_column('comments', 'image_key')
    op.drop_column('comments', 'parent_id')
