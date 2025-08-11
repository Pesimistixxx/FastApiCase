"""add achievements3

Revision ID: 84e891a13bea
Revises: c56e778158ca
Create Date: 2025-08-11 17:33:16.165180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '84e891a13bea'
down_revision: Union[str, None] = 'c56e778158ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

achievements_table = sa.Table(
    'achievements',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(255), nullable=False),
    sa.Column('is_active', sa.Boolean, default=True),
    sa.Column('image', sa.String(255), default='default.png'),
    sa.Column('description', sa.String(255))
)


def upgrade() -> None:
    op.bulk_insert(
        achievements_table,
        [
            {
                'name': 'Создатель КС',
                'description': "Создать свой первый кейс",
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Кейсовый барон',
                'description': "Создать 10 кейсов",
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Кейсовый конвеер',
                'description': "Создать 100 кейсов",
                'is_active': True,
                'image': 'default.png'
            }

        ])


def downgrade() -> None:
    op.execute(
        achievements_table.delete().where(
            achievements_table.c.name.in_(['Создатель КС', 'Кейсовый барон', 'Кейсовый конвеер'])
        )
    )
