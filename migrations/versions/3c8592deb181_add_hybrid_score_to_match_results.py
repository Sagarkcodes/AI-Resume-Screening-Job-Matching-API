"""add hybrid score to match results

Revision ID: 3c8592deb181
Revises: b3d5409f63af
Create Date: 2026-10-14 01:22:34.229267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c8592deb181'
down_revision: Union[str, Sequence[str], None] = 'b3d5409f63af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column(
            "hybrid_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
    )

    op.alter_column(
        "match_results",
        "hybrid_score",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("match_results", "hybrid_score")
