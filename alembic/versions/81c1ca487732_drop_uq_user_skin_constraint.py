"""drop uq_user_skin constraint

Revision ID: 81c1ca487732
Revises: 6d9b6531f8bb
Create Date: 2025-07-03 13:23:49.123309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
            ALTER TABLE users_skins 
            DROP CONSTRAINT IF EXISTS uq_user_skin
        """)


def downgrade():
    op.execute("""
            ALTER TABLE users_skins 
            ADD CONSTRAINT uq_user_skin 
            UNIQUE (user_id, skin_id)
        """)


# revision identifiers, used by Alembic.
revision: str = '81c1ca487732'
down_revision: Union[str, None] = '6d9b6531f8bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
