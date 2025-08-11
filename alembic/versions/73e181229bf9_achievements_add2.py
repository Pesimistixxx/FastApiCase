"""achievements add2

Revision ID: 73e181229bf9
Revises: a9a5ab930183
Create Date: 2025-08-11 15:46:55.821575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73e181229bf9'
down_revision: Union[str, None] = 'a9a5ab930183'
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
                'name': 'Невозможно',
                'description': "Выбить AWP Удар Молнии из кейса 'Удар молнии фарм'",
                'is_active': True,
                'image': 'default.png'
            }])


def downgrade() -> None:
    op.execute(
        achievements_table.delete().where(
            achievements_table.c.name.in_(['Невозможно'])
        )
    )
