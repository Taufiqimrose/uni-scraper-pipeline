# Uni Scraper Pipeline

> AI-powered agentic scraping pipeline that extracts academic programs, courses, and degree requirements from **any** university website.

[![CI](https://github.com/YOUR_USERNAME/uni-scraper-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/uni-scraper-pipeline/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What It Does

Submit any university catalog URL and the pipeline will:

1. **Analyze** the site structure using GPT-4o
2. **Discover** all academic programs (majors, minors, certificates)
3. **Extract** degree requirements, courses, prerequisites, and unit counts
4. **Validate** data completeness and quality
5. **Store** structured data in PostgreSQL (Supabase)

All through an intelligent agent that adapts to different university website layouts.

## Architecture

```
                        +------------------+
                        |   Next.js App    |
                        |  (Schedia.AI)    |
                        +--------+---------+
                                 |
                            REST API
                                 |
+--------------------------------v---------------------------------+
|                    Uni Scraper Pipeline                           |
|                                                                  |
|  +------------------+    +------------------------------------+  |
|  |  FastAPI Server  |    |         Orchestrator               |  |
|  |                  |    |   (Plan - Execute - Observe)       |  |
|  |  POST /scrape    +--->+                                    |  |
|  |  GET  /status    |    |  Planner -> Navigator -> Extractor |  |
|  |  GET  /programs  |    |              |                     |  |
|  +------------------+    |           Validator                |  |
|                          +----+----------+----------+---------+  |
|                               |          |          |            |
|                    +----------v--+ +-----v----+ +---v---------+  |
|                    |  Playwright | | GPT-4o   | |  Supabase   |  |
|                    |  (Browser)  | | (OpenAI) | | (PostgreSQL)|  |
|                    +-------------+ +----------+ +-------------+  |
+------------------------------------------------------------------+
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL (or Supabase account)
- OpenAI API key

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/uni-scraper-pipeline.git
cd uni-scraper-pipeline

# Install dependencies
make dev

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys and database URL

# Run database migrations (happens automatically on server start)
```

### Run the Server

```bash
make serve
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Scrape a University

```bash
# Via CLI
make scrape URL=https://catalog.csus.edu NAME="Sacramento State"

# Via API
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "https://catalog.csus.edu", "university_name": "Sacramento State"}'
```

### Docker

```bash
docker compose up
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scrape` | Start a new scraping job |
| `GET` | `/api/v1/scrape/{job_id}` | Get job status and progress |
| `GET` | `/api/v1/scrape/{job_id}/log` | Get agent decision log |
| `DELETE` | `/api/v1/scrape/{job_id}` | Cancel a running job |
| `GET` | `/api/v1/universities` | List scraped universities |
| `GET` | `/api/v1/universities/{id}` | Get university details |
| `GET` | `/api/v1/universities/{id}/programs` | List programs |
| `GET` | `/api/v1/programs/{id}` | Get program with requirements |
| `GET` | `/api/v1/universities/{id}/courses` | List courses |
| `GET` | `/api/v1/courses/{id}` | Get course with prerequisites |
| `GET` | `/api/v1/health` | Health check |

Full OpenAPI docs available at `/docs` when the server is running.

## How the Agent Works

The pipeline uses a **Plan-Execute-Observe** loop powered by GPT-4o:

```
Phase 1: PLANNER
  Input:  Seed URL HTML
  Output: NavigationPlan (site type, program list URLs, strategy)

Phase 2: NAVIGATOR
  Input:  Program list pages
  Output: List of DiscoveredProgram (name, URL, degree type)

Phase 3: EXTRACTOR
  Input:  Each program detail page
  Output: ProgramDetail (requirements, courses, prerequisites)

Phase 4: VALIDATOR
  Input:  All extracted data
  Output: ValidationReport (completeness score, issues, recommendations)

Phase 5: STORER
  Input:  Validated data
  Output: Records in PostgreSQL
```

Each phase uses GPT-4o with structured JSON output and Pydantic validation. The agent handles:

- Pagination and multi-page navigation
- JavaScript-rendered pages (via Playwright)
- robots.txt compliance and rate limiting
- Automatic retries with exponential backoff
- Token budget tracking to control costs
- Graceful degradation (partial results on failure)

## Project Structure

```
src/
  api/          # FastAPI server, routes, middleware
  agent/        # AI agents (planner, navigator, extractor, validator)
    prompts/    # GPT-4o prompt templates
  browser/      # Playwright browser pool, page fetcher, HTML cleaner
  models/       # Pydantic models (domain, API schemas, agent state)
  db/           # Database connection, repositories, migrations
  queue/        # Background job worker
  cache/        # Page cache with TTL
  config/       # Settings, logging
  utils/        # URL utils, text utils, retry decorators, token counter
tests/
  unit/         # Unit tests
  integration/  # Integration tests
  fixtures/     # Sample HTML and expected outputs
scripts/        # CLI tools
```

## Data Model

```
universities 1--* programs 1--* requirement_groups 1--* program_requirements
                                                              |
universities 1--* catalog_courses 1--* prerequisites    course reference
```

- **University**: name, domain, catalog URL, program count
- **Program**: name, degree type (BS/BA/MS/PhD/etc), department, total units
- **Course**: code (CSC 130), title, units, description
- **Prerequisite**: course relationships with OR-group support
- **Requirement Group**: logical sections (Core, Electives, Gen Ed)

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run linter
make lint

# Format code
make format

# Type check
make typecheck

# Run all checks
make check
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| API Framework | FastAPI |
| AI Model | OpenAI GPT-4o |
| Browser Automation | Playwright |
| Database | PostgreSQL (Supabase) |
| DB Driver | asyncpg |
| HTML Parsing | BeautifulSoup4 + lxml |
| HTTP Client | httpx |
| Validation | Pydantic v2 |
| Logging | structlog |
| Package Manager | uv |
| Linter/Formatter | Ruff |
| Type Checker | mypy |
| CI/CD | GitHub Actions |

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `API_KEY` | Yes | - | API key for authentication |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model to use |
| `TOKEN_BUDGET` | No | `2000000` | Max tokens per scrape job |
| `BROWSER_POOL_SIZE` | No | `3` | Concurrent browser contexts |
| `RATE_LIMIT_DELAY` | No | `2.0` | Seconds between requests to same domain |
| `CACHE_TTL_HOURS` | No | `24` | Page cache expiry |

## License

MIT - see [LICENSE](LICENSE)
