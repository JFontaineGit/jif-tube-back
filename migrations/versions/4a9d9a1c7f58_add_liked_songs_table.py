"""add liked songs table

Revision ID: 4a9d9a1c7f58
Revises: cf077f509068
Create Date: 2024-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4a9d9a1c7f58'
down_revision: Union[str, Sequence[str], None] = 'cf077f509068'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create liked_songs table."""
    op.create_table(
        'liked_songs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('song_id', sa.String(length=255), nullable=False),
        sa.Column('liked_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'song_id', name='unique_liked_song')
    )
    op.create_index('ix_liked_songs_user_id', 'liked_songs', ['user_id'], unique=False)
    op.create_index('ix_liked_songs_song_id', 'liked_songs', ['song_id'], unique=False)


def downgrade() -> None:
    """Drop liked_songs table."""
    op.drop_index('ix_liked_songs_song_id', table_name='liked_songs')
    op.drop_index('ix_liked_songs_user_id', table_name='liked_songs')
    op.drop_table('liked_songs')
