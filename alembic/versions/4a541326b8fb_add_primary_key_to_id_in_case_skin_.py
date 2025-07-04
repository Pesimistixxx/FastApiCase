"""Add primary key to id in Case_Skin relation

Revision ID: 4a541326b8fb
Revises: 136e94d9fbca
Create Date: 2025-07-03 20:48:34.151011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a541326b8fb'
down_revision: Union[str, None] = '136e94d9fbca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE case_models
        ADD CONSTRAINT pk_case_models_id PRIMARY KEY (id)
    """)
    pass


def downgrade() -> None:
    op.execute("""
            ALTER TABLE case_models
            DROP CONSTRAINT pk_case_models_id
        """)
    pass
