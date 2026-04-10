"""Add canonical product columns to discounts table.

Revision ID: 0002_canonicalization
Revises: 3a2ff79b0965
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_canonicalization"
down_revision = "3a2ff79b0965"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discounts", sa.Column("canonical_brand", sa.String(256), nullable=True))
    op.add_column("discounts", sa.Column("canonical_product_type", sa.String(128), nullable=True))
    op.add_column("discounts", sa.Column("canonical_quantity_value", sa.Float(), nullable=True))
    op.add_column("discounts", sa.Column("canonical_quantity_unit", sa.String(16), nullable=True))
    op.add_column("discounts", sa.Column("canonical_key", sa.String(512), nullable=True))
    op.create_index("ix_discounts_canonical_key", "discounts", ["canonical_key"])


def downgrade() -> None:
    op.drop_index("ix_discounts_canonical_key", table_name="discounts")
    op.drop_column("discounts", "canonical_key")
    op.drop_column("discounts", "canonical_quantity_unit")
    op.drop_column("discounts", "canonical_quantity_value")
    op.drop_column("discounts", "canonical_product_type")
    op.drop_column("discounts", "canonical_brand")
