"""make isbn10 the books primary key

Revision ID: a1b2c3d4e5f6
Revises: 3e2a0979436d
Create Date: 2026-08-17 03:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3e2a0979436d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are empty at this stage; recreate books/ratings around isbn10.
    op.drop_table("ratings")
    op.drop_table("books")

    op.create_table(
        "books",
        sa.Column("isbn10", sa.String(), nullable=False),
        sa.Column("isbn13", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subtitle", sa.String(), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(), nullable=True),
        sa.Column("published_year", sa.Integer(), nullable=True),
        sa.Column("num_pages", sa.Integer(), nullable=True),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("ratings_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("isbn10"),
        sa.UniqueConstraint("isbn13"),
    )
    op.create_table(
        "ratings",
        sa.Column("rating_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roll_number", sa.String(), nullable=False),
        sa.Column("isbn10", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["isbn10"], ["books.isbn10"]),
        sa.ForeignKeyConstraint(["roll_number"], ["users.roll_number"]),
        sa.PrimaryKeyConstraint("rating_id"),
        sa.UniqueConstraint("roll_number", "isbn10", name="uq_rating_user_book"),
    )


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_table("books")

    op.create_table(
        "books",
        sa.Column("book_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("isbn10", sa.String(), nullable=True),
        sa.Column("isbn13", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subtitle", sa.String(), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(), nullable=True),
        sa.Column("published_year", sa.Integer(), nullable=True),
        sa.Column("num_pages", sa.Integer(), nullable=True),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("ratings_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("book_id"),
        sa.UniqueConstraint("isbn10"),
        sa.UniqueConstraint("isbn13"),
    )
    op.create_table(
        "ratings",
        sa.Column("rating_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roll_number", sa.String(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.book_id"]),
        sa.ForeignKeyConstraint(["roll_number"], ["users.roll_number"]),
        sa.PrimaryKeyConstraint("rating_id"),
        sa.UniqueConstraint("roll_number", "book_id", name="uq_rating_user_book"),
    )
