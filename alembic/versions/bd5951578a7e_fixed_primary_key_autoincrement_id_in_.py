"""Fixed primary key(autoincrement) id in Case_Skin relation

Revision ID: bd5951578a7e
Revises: 4a541326b8fb
Create Date: 2025-07-03 21:00:05.354274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd5951578a7e'
down_revision: Union[str, None] = '4a541326b8fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(sa.schema.CreateSequence(sa.Sequence("case_models_id_seq")))

    op.alter_column(
        "case_models",
        "id",
        server_default=sa.text("nextval('case_models_id_seq'::regclass)"),
        existing_type=sa.INTEGER(),
        existing_nullable=False,
        existing_primary_key=True
    )

    op.execute(sa.text("SELECT setval('case_models_id_seq', (SELECT MAX(id) FROM case_models))"))


def downgrade():
    op.alter_column(
        "case_models",
        "id",
        server_default=None,
        existing_type=sa.INTEGER(),
        existing_nullable=False,
        existing_primary_key=True
    )

    op.execute(sa.schema.DropSequence(sa.Sequence("case_models_id_seq")))
