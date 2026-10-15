"""add semantic score to match results

Revision ID: b3d5409f63af
Revises: ea60ba919037
Create Date: 2026-10-13 19:12:44.892025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d5409f63af'
down_revision: Union[str, Sequence[str], None] = 'ea60ba919037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column(
            "semantic_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
    )

    # Remove the database default after existing rows are populated.
    op.alter_column(
        "match_results",
        "semantic_score",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("match_results", "semantic_score")
