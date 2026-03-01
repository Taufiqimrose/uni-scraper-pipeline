from uuid import UUID

import asyncpg
import structlog

from src.models import Program

logger = structlog.get_logger()


class ProgramRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(self, program: Program) -> Program:
        """Insert or update a program record."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO programs (id, university_id, name, degree_type, department, description, source_url, total_units, catalog_year)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (university_id, name, degree_type) DO UPDATE SET
                    department = EXCLUDED.department,
                    description = EXCLUDED.description,
                    source_url = EXCLUDED.source_url,
                    total_units = EXCLUDED.total_units,
                    catalog_year = EXCLUDED.catalog_year
                RETURNING *
                """,
                program.id,
                program.university_id,
                program.name,
                program.degree_type.value,
                program.department,
                program.description,
                program.source_url,
                program.total_units,
                program.catalog_year,
            )
            return Program(**dict(row))

    async def get_by_id(self, program_id: UUID) -> Program | None:
        """Get a program by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM programs WHERE id = $1", program_id)
            return Program(**dict(row)) if row else None

    async def list_by_university(
        self,
        university_id: UUID,
        degree_type: str | None = None,
        department: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Program], int]:
        """List programs for a university with optional filters."""
        conditions = ["university_id = $1"]
        params: list[object] = [university_id]
        idx = 2

        if degree_type:
            conditions.append(f"degree_type = ${idx}")
            params.append(degree_type)
            idx += 1

        if department:
            conditions.append(f"department ILIKE ${idx}")
            params.append(f"%{department}%")
            idx += 1

        if search:
            conditions.append(f"name ILIKE ${idx}")
            params.append(f"%{search}%")
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}"

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM programs {where}", *params
            )
            rows = await conn.fetch(
                f"SELECT * FROM programs {where} ORDER BY name LIMIT ${idx} OFFSET ${idx + 1}",
                *params,
                page_size,
                (page - 1) * page_size,
            )
            return [Program(**dict(r)) for r in rows], total or 0

    async def bulk_upsert(self, programs: list[Program]) -> int:
        """Upsert multiple programs in a transaction. Returns count of upserted rows."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                count = 0
                for program in programs:
                    await conn.execute(
                        """
                        INSERT INTO programs (id, university_id, name, degree_type, department, description, source_url, total_units, catalog_year)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (university_id, name, degree_type) DO UPDATE SET
                            department = EXCLUDED.department,
                            description = EXCLUDED.description,
                            source_url = EXCLUDED.source_url,
                            total_units = EXCLUDED.total_units,
                            catalog_year = EXCLUDED.catalog_year
                        """,
                        program.id,
                        program.university_id,
                        program.name,
                        program.degree_type.value,
                        program.department,
                        program.description,
                        program.source_url,
                        program.total_units,
                        program.catalog_year,
                    )
                    count += 1
                return count
