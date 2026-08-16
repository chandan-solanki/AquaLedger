"""document records table

Revision ID: c4e9a2f1d7b3
Revises: b8d1f4a726c9
Create Date: 2026-08-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e9a2f1d7b3"
down_revision: Union[str, Sequence[str], None] = "b8d1f4a726c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "document_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("document_number", sa.String(length=50), nullable=False),
        sa.Column("party_type", sa.String(length=20), nullable=True),
        sa.Column("party_id", sa.UUID(), nullable=True),
        sa.Column("party_name", sa.String(length=255), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=10), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("generated_by", sa.UUID(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["generated_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_records_tenant", "document_records", ["tenant_id"], unique=False)
    op.create_index(
        "ix_document_records_tenant_type",
        "document_records",
        ["tenant_id", "document_type"],
        unique=False,
    )
    op.create_index(
        "ix_document_records_tenant_generated_at",
        "document_records",
        ["tenant_id", "generated_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_records_tenant_document_number",
        "document_records",
        ["tenant_id", "document_number"],
        unique=False,
    )
    op.create_index(
        "ix_document_records_tenant_party",
        "document_records",
        ["tenant_id", "party_type", "party_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_document_records_tenant_party", table_name="document_records")
    op.drop_index("ix_document_records_tenant_document_number", table_name="document_records")
    op.drop_index("ix_document_records_tenant_generated_at", table_name="document_records")
    op.drop_index("ix_document_records_tenant_type", table_name="document_records")
    op.drop_index("ix_document_records_tenant", table_name="document_records")
    op.drop_table("document_records")
