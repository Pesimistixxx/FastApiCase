"""add created to battles

Revision ID: adbcfa3e3cdc
Revises: 1c60287f206d
Create Date: 2025-08-03 14:07:50.756673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'adbcfa3e3cdc'
down_revision: Union[str, None] = '1c60287f206d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Переименовываем таблицу вместо удаления/создания
    op.rename_table('case_models', 'cases_skins')

    # Добавляем created в battles и удаляем expires
    op.add_column('battles', sa.Column('created', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.drop_column('battles', 'expires')


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем expires и удаляем created
    op.add_column('battles', sa.Column('expires', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.drop_column('battles', 'created')

    # Возвращаем старое имя таблицы
    op.rename_table('cases_skins', 'case_models')