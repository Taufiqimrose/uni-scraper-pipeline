-- ============================================================
-- Uni-Scraper-Pipeline: Initial Database Schema
-- ============================================================

-- Universities
CREATE TABLE IF NOT EXISTS universities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    domain          TEXT NOT NULL,
    catalog_url     TEXT NOT NULL,
    logo_url        TEXT,
    state           TEXT,
    country         TEXT NOT NULL DEFAULT 'US',
    program_count   INTEGER NOT NULL DEFAULT 0,
    last_scraped_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_universities_slug ON universities(slug);
CREATE INDEX IF NOT EXISTS idx_universities_domain ON universities(domain);

-- Programs (Majors/Minors/Certificates)
CREATE TABLE IF NOT EXISTS programs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id   UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    degree_type     TEXT NOT NULL,
    department      TEXT,
    description     TEXT,
    source_url      TEXT NOT NULL,
    total_units     INTEGER,
    catalog_year    TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(university_id, name, degree_type)
);

CREATE INDEX IF NOT EXISTS idx_programs_university ON programs(university_id);
CREATE INDEX IF NOT EXISTS idx_programs_degree_type ON programs(degree_type);

-- Courses (catalog-level, separate from user courses)
CREATE TABLE IF NOT EXISTS catalog_courses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id   UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    units           INTEGER NOT NULL,
    department      TEXT,
    source_url      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(university_id, code)
);

CREATE INDEX IF NOT EXISTS idx_catalog_courses_university ON catalog_courses(university_id);
CREATE INDEX IF NOT EXISTS idx_catalog_courses_code ON catalog_courses(code);

-- Prerequisites
CREATE TABLE IF NOT EXISTS prerequisites (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id               UUID NOT NULL REFERENCES catalog_courses(id) ON DELETE CASCADE,
    prerequisite_course_id  UUID REFERENCES catalog_courses(id) ON DELETE SET NULL,
    prerequisite_code       TEXT NOT NULL,
    is_corequisite          BOOLEAN NOT NULL DEFAULT false,
    group_id                INTEGER NOT NULL DEFAULT 0,
    notes                   TEXT,
    UNIQUE(course_id, prerequisite_code)
);

CREATE INDEX IF NOT EXISTS idx_prerequisites_course ON prerequisites(course_id);

-- Requirement Groups
CREATE TABLE IF NOT EXISTS requirement_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id      UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    units_required  INTEGER,
    courses_required INTEGER,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    UNIQUE(program_id, name)
);

CREATE INDEX IF NOT EXISTS idx_req_groups_program ON requirement_groups(program_id);

-- Program Requirements (courses within requirement groups)
CREATE TABLE IF NOT EXISTS program_requirements (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_group_id UUID NOT NULL REFERENCES requirement_groups(id) ON DELETE CASCADE,
    course_id            UUID REFERENCES catalog_courses(id) ON DELETE SET NULL,
    course_code          TEXT NOT NULL,
    course_title         TEXT NOT NULL,
    units                INTEGER NOT NULL,
    is_required          BOOLEAN NOT NULL DEFAULT true,
    alternatives         TEXT[] DEFAULT '{}',
    sort_order           INTEGER NOT NULL DEFAULT 0,
    notes                TEXT
);

CREATE INDEX IF NOT EXISTS idx_prog_reqs_group ON program_requirements(requirement_group_id);

-- Scrape Jobs
CREATE TABLE IF NOT EXISTS scrape_jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_name     TEXT NOT NULL,
    seed_url            TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'queued',
    progress            REAL NOT NULL DEFAULT 0.0,
    current_step        TEXT,
    programs_found      INTEGER NOT NULL DEFAULT 0,
    programs_scraped    INTEGER NOT NULL DEFAULT 0,
    courses_found       INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    error_details       JSONB,
    agent_log           JSONB DEFAULT '[]',
    total_tokens_used   INTEGER NOT NULL DEFAULT 0,
    total_pages_fetched INTEGER NOT NULL DEFAULT 0,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status ON scrape_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_created ON scrape_jobs(created_at DESC);

-- Page Cache
CREATE TABLE IF NOT EXISTS page_cache (
    url_hash        TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    content_html    TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_page_cache_expires ON page_cache(expires_at);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER trg_universities_updated BEFORE UPDATE ON universities
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_programs_updated BEFORE UPDATE ON programs
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_catalog_courses_updated BEFORE UPDATE ON catalog_courses
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
