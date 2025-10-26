"""convert integer identifiers to uuid"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "887bef1d75a4"
down_revision: Union[str, Sequence[str], None] = "4a9d9a1c7f58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Switch integer identifiers to UUID across user-bound tables."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
    )
    op.alter_column("users", "uuid", server_default=None)

    # ------------------------------------------------------------------
    # Search history
    # ------------------------------------------------------------------
    op.add_column(
        "search_history",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
    )
    op.add_column(
        "search_history",
        sa.Column("user_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE search_history AS sh
        SET user_uuid = u.uuid
        FROM users AS u
        WHERE sh.user_id = u.id
        """
    )
    op.alter_column("search_history", "uuid", server_default=None)

    # ------------------------------------------------------------------
    # Library entries
    # ------------------------------------------------------------------
    op.add_column(
        "user_library",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_library",
        sa.Column("user_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE user_library AS ul
        SET user_uuid = u.uuid
        FROM users AS u
        WHERE ul.user_id = u.id
        """
    )
    op.alter_column("user_library", "user_uuid", nullable=False)
    op.alter_column("user_library", "uuid", server_default=None)

    # ------------------------------------------------------------------
    # Liked songs
    # ------------------------------------------------------------------
    op.add_column(
        "liked_songs",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
    )
    op.add_column(
        "liked_songs",
        sa.Column("user_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE liked_songs AS ls
        SET user_uuid = u.uuid
        FROM users AS u
        WHERE ls.user_id = u.id
        """
    )
    op.alter_column("liked_songs", "user_uuid", nullable=False)
    op.alter_column("liked_songs", "uuid", server_default=None)

    # ------------------------------------------------------------------
    # Drop legacy constraints / columns
    # ------------------------------------------------------------------
    op.drop_constraint("search_history_user_id_fkey", "search_history", type_="foreignkey")
    op.drop_index("ix_search_history_user_id", table_name="search_history")
    op.drop_constraint("search_history_pkey", "search_history", type_="primary")

    op.drop_constraint("unique_user_song", "user_library", type_="unique")
    op.drop_constraint("user_library_user_id_fkey", "user_library", type_="foreignkey")
    op.drop_constraint("user_library_pkey", "user_library", type_="primary")

    op.drop_constraint("unique_liked_song", "liked_songs", type_="unique")
    op.drop_index("ix_liked_songs_user_id", table_name="liked_songs")
    op.drop_constraint("liked_songs_user_id_fkey", "liked_songs", type_="foreignkey")
    op.drop_constraint("liked_songs_pkey", "liked_songs", type_="primary")

    op.drop_column("search_history", "user_id")
    op.drop_column("search_history", "id")
    op.drop_column("user_library", "user_id")
    op.drop_column("user_library", "id")
    op.drop_column("liked_songs", "user_id")
    op.drop_column("liked_songs", "id")
    op.drop_constraint("users_pkey", "users", type_="primary")
    op.drop_column("users", "id")

    op.execute("DROP SEQUENCE IF EXISTS search_history_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS user_library_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS liked_songs_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS users_id_seq")

    # ------------------------------------------------------------------
    # Rename new uuid columns to canonical names
    # ------------------------------------------------------------------
    op.alter_column("users", "uuid", new_column_name="id")
    op.alter_column("search_history", "uuid", new_column_name="id")
    op.alter_column("search_history", "user_uuid", new_column_name="user_id")
    op.alter_column("user_library", "uuid", new_column_name="id")
    op.alter_column("user_library", "user_uuid", new_column_name="user_id")
    op.alter_column("liked_songs", "uuid", new_column_name="id")
    op.alter_column("liked_songs", "user_uuid", new_column_name="user_id")

    # ------------------------------------------------------------------
    # Recreate constraints on UUID columns
    # ------------------------------------------------------------------
    op.create_primary_key("users_pkey", "users", ["id"])

    op.create_primary_key("search_history_pkey", "search_history", ["id"])
    op.create_foreign_key(
        "search_history_user_id_fkey",
        "search_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("search_history", "user_id", nullable=True)
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"], unique=False)

    op.create_primary_key("user_library_pkey", "user_library", ["id"])
    op.create_foreign_key(
        "user_library_user_id_fkey",
        "user_library",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("user_library", "user_id", nullable=False)
    op.create_unique_constraint("unique_user_song", "user_library", ["user_id", "song_id"])

    op.create_primary_key("liked_songs_pkey", "liked_songs", ["id"])
    op.create_foreign_key(
        "liked_songs_user_id_fkey",
        "liked_songs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("liked_songs", "user_id", nullable=False)
    op.create_unique_constraint("unique_liked_song", "liked_songs", ["user_id", "song_id"])
    op.create_index("ix_liked_songs_user_id", "liked_songs", ["user_id"], unique=False)

    # Reinstate helpful defaults
    op.alter_column("users", "id", server_default=sa.text("uuid_generate_v4()"))
    op.alter_column("search_history", "id", server_default=sa.text("uuid_generate_v4()"))
    op.alter_column("user_library", "id", server_default=sa.text("uuid_generate_v4()"))
    op.alter_column("liked_songs", "id", server_default=sa.text("uuid_generate_v4()"))


def downgrade() -> None:
    """Downgrade is intentionally not supported for UUID migration."""
    raise NotImplementedError("Downgrade is not supported for the UUID migration")
