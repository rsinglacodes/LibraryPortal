import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database.connection import get_engine

def init_user_interactions_table():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS user_interactions CASCADE;"))
        conn.execute(text("""
            CREATE TABLE user_interactions (
                id SERIAL PRIMARY KEY,
                roll_number VARCHAR(64) NOT NULL,
                interaction_type VARCHAR(32) NOT NULL,
                content TEXT,
                isbn10 VARCHAR(10),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_interactions_roll_number ON user_interactions(roll_number);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_interactions_interaction_type ON user_interactions(interaction_type);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_interactions_isbn10 ON user_interactions(isbn10);"))
        conn.commit()
        print("Table user_interactions created successfully!")

if __name__ == "__main__":
    init_user_interactions_table()
