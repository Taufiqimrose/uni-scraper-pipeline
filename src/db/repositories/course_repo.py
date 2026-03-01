from uuid import UUID

import asyncpg
import structlog

from src.models import Course

logger = structlog.get_logger()


class CourseRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(self, course: Course) -> Course:
        """Insert or update a catalog course."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO catalog_courses (id, university_id, code, title, description, units, department, source_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (university_id, code) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    units = EXCLUDED.units,
                    department = EXCLUDED.department,
                    source_url = EXCLUDED.source_url
                RETURNING *
                """,
                course.id,
                course.university_id,
                course.code,
                course.title,
                course.description,
                course.units,
                course.department,
                course.source_url,
            )
            return Course(**dict(row))

    async def get_by_id(self, course_id: UUID) -> Course | None:
        """Get a course by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM catalog_courses WHERE id = $1", course_id)
            return Course(**dict(row)) if row else None

    async def get_by_code(self, university_id: UUID, code: str) -> Course | None:
        """Get a course by university + code."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM catalog_courses WHERE university_id = $1 AND code = $2",
                university_id,
                code,
            )
            return Course(**dict(row)) if row else None

    async def list_by_university(
        self,
        university_id: UUID,
        department: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Course], int]:
        """List courses for a university."""
        conditions = ["university_id = $1"]
        params: list[object] = [university_id]
        idx = 2

        if department:
            conditions.append(f"department ILIKE ${idx}")
            params.append(f"%{department}%")
            idx += 1

        if search:
            conditions.append(f"(code ILIKE ${idx} OR title ILIKE ${idx})")
            params.append(f"%{search}%")
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}"

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM catalog_courses {where}", *params
            )
            rows = await conn.fetch(
                f"SELECT * FROM catalog_courses {where} ORDER BY code LIMIT ${idx} OFFSET ${idx + 1}",
                *params,
                page_size,
                (page - 1) * page_size,
            )
            return [Course(**dict(r)) for r in rows], total or 0

    async def bulk_upsert(self, courses: list[Course]) -> int:
        """Upsert multiple courses in a transaction."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                count = 0
                for course in courses:
                    await conn.execute(
                        """
                        INSERT INTO catalog_courses (id, university_id, code, title, description, units, department, source_url)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (university_id, code) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            units = EXCLUDED.units,
                            department = EXCLUDED.department,
                            source_url = EXCLUDED.source_url
                        """,
                        course.id,
                        course.university_id,
                        course.code,
                        course.title,
                        course.description,
                        course.units,
                        course.department,
                        course.source_url,
                    )
                    count += 1
                return count
