"""add skins - users relation

Revision ID: d3ceade5c938
Revises: 2145c4cc6aa4
Create Date: 2025-06-30 20:31:38.226733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3ceade5c938'
down_revision: Union[str, None] = '2145c4cc6aa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users_skins',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('skin_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['skin_id'], ['skins.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'skin_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users_skins')
    # ### end Alembic commands ###
