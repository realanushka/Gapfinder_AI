"""Verify the live database matches what the migration was supposed to create.

Run after `alembic upgrade head`:
    python -m scripts.verify_db

Checks the pgvector extension, all ten tables from ARCHITECTURE.md section 3, the
HNSW index that every retrieval path depends on, the enum labels, and the stamped
Alembic revision. Exits non-zero if anything is missing.
"""

import asyncio
import sys

from sqlalchemy import text

from app.database import engine

EXPECTED_TABLES = [
    "attempts",
    "chunk_topics",
    "chunks",
    "documents",
    "past_questions",
    "plans",
    "questions",
    "topic_scores",
    "topics",
    "users",
]

EXPECTED_ENUMS = {
    "documenttype": ["syllabus", "notes", "textbook", "past_paper"],
    "masterystatus": ["weak", "medium", "strong"],
}


async def main() -> int:
    failures: list[str] = []

    async with engine.connect() as conn:
        version = await conn.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        if version:
            print(f"[ok]   pgvector extension installed (v{version})")
        else:
            failures.append("pgvector extension is NOT installed")

        rows = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        present = {r[0] for r in rows}
        missing = [t for t in EXPECTED_TABLES if t not in present]
        if missing:
            failures.append(f"missing tables: {', '.join(missing)}")
        else:
            print(f"[ok]   all {len(EXPECTED_TABLES)} tables present")

        index_def = await conn.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_chunks_embedding_hnsw'")
        )
        if not index_def:
            failures.append("HNSW index ix_chunks_embedding_hnsw is missing")
        elif "vector_cosine_ops" not in index_def:
            failures.append(f"HNSW index has the wrong opclass: {index_def}")
        else:
            print("[ok]   HNSW index on chunks.embedding uses vector_cosine_ops")

        for enum_name, expected_labels in EXPECTED_ENUMS.items():
            rows = await conn.execute(
                text(
                    "SELECT e.enumlabel FROM pg_enum e "
                    "JOIN pg_type t ON t.oid = e.enumtypid "
                    "WHERE t.typname = :name ORDER BY e.enumsortorder"
                ),
                {"name": enum_name},
            )
            labels = [r[0] for r in rows]
            if not labels:
                failures.append(f"enum type {enum_name} is missing")
            elif labels != expected_labels:
                failures.append(f"enum {enum_name} labels are {labels}, expected {expected_labels}")
            else:
                print(f"[ok]   enum {enum_name} = {labels}")

        revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
        if revision:
            print(f"[ok]   alembic revision stamped: {revision}")
        else:
            failures.append("alembic_version table is empty")

    await engine.dispose()

    print()
    if failures:
        print("FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Database verified.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
