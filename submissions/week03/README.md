# Week 3 Submission — Individual Readiness Lab

## Student information

- Name: Li Xiaolong (李小龙)
- Student ID: 21341720
- Repository: https://github.com/lxl1067/MAIE6000c-starter-Long-private
- Checkpoint tag: `w03-readiness`
- Commit SHA: this commit — it is the single commit tagged `w03-readiness`;
  read it back with `git rev-parse w03-readiness^{commit}`
- Course: MAIE 6000C — W03 Individual Readiness Lab (required tag `w03-readiness`)

## 1. What I changed

**One bounded change: the API readiness endpoint now actually reports readiness.**

Before, `/health/ready` executed `SELECT 1` and then always returned
`{"service": "api", "status": "ok"}`. If the database were unreachable the
exception escaped as an unhandled server error, and the endpoint advertised
"ok" without ever telling the caller what it had checked.

Now the endpoint treats a failing probe as a readiness failure:

| Situation | Status | Body |
| --- | --- | --- |
| Probe succeeds | `200` | `{"service":"api","status":"ok","version":"0.1.0","database":"ok"}` |
| Probe fails | `503` | `{"service":"api","status":"unavailable","error":"database"}` |

A failing probe also emits an error-level `readiness_check_failed` log line with
`dependency=database` and the underlying error text, so the failure is visible in
the structured logs and in the request metrics, not just to the caller.

The reported `version` comes from a single `SERVICE_VERSION` constant in
`services/common/config.py`, which is also the FastAPI `version` for both the API
and the AI service. Before this change the version string was duplicated as a
literal in each service, so the number a health check reported could drift from
the deployed version.

**Supporting change inside the same bounded scope: repair and extend the
verification around this endpoint.**

- `tests/integration/test_api_health.py` is new: it checks the live endpoint,
  the happy-path ready payload, and the `503` path.
- `tests/integration/test_api_integration.py python` was a real, silent defect:
  its trailing ` python` means the file name never matched pytest's `test_*.py`
  collection pattern, so the two tests inside it had never run. The unique test
  (`test_create_case_enqueues_job`) is restored in `test_api_case_flow.py`, and
  the duplicate health assertion is dropped in favour of the new file.
- `tests/conftest.py` now creates each throwaway SQLite test database in the
  git-ignored, repository-local `.pytest_tmp/` directory instead of depending on
  a writable OS temp directory.
- `docs/operations.md` documents the health contract and the test scratch
  location.

Kept deliberately small: no new dependency, no schema or migration change, no
route behaviour change outside `/health/ready`, and the AI service keeps its
existing (dependency-free) readiness shape plus the shared version value.

## 2. Files touched

- `services/api/app/main.py` — readiness probe and `503` response
- `services/common/schemas.py` — `HealthResponse` gains optional `version`/`database`; adds `ServiceErrorResponse`
- `services/common/config.py` — adds the shared `SERVICE_VERSION`
- `services/ai/app/main.py` — reports the shared version from `/health/ready`
- `tests/integration/test_api_health.py` — new readiness tests
- `tests/integration/test_api_case_flow.py` — recovers the never-collected test
- `tests/integration/test_api_integration.py python` — removed (mis-named file, contents recovered)
- `tests/conftest.py` — repo-local test scratch directory
- `docs/operations.md` — health contract and test scratch docs
- `.gitignore` — ignores `.pytest_tmp/`

## 3. How I verified it

1. **Unit + integration suite passes.**
   `pytest -q tests/unit tests/integration` → `8 passed` (was `4 passed` with
   2 tests silently uncollected before the repair).
2. **The `503` path is covered by a test that fails without the change.**
   `test_health_ready_returns_503_when_database_probe_fails` monkeypatches the
   session so `SELECT 1` raises `OperationalError`; the route must answer `503`
   with `error=database`. Remove the `try`/`except` and this test fails, so the
   test is tied to the behaviour rather than to the code shape.
3. **Lint is clean.** `ruff check .` → `All checks passed!`
4. **Migration applies.** `alembic upgrade head` applied the repository's
   `20260713_0001` migration cleanly and produced the `cases` and `jobs` tables.
5. **Real end-to-end run, not just tests.** With the API, AI service, and worker
   running as three separate local processes (SQLite instead of PostgreSQL,
   because no Docker daemon was reachable in this environment), the repository's
   own smoke test passed against the live stack:
   `SMOKE_BASE_URL=http://127.0.0.1:8000 pytest tests/smoke -q` → `1 passed`.
   The persisted rows confirm the whole path through a real HTTP boundary:
   `cases`: `Production outage alert` → `triaged`, `ai_label=incident`,
   `ai_confidence=0.71`; `jobs`: `triage_case` → `completed`, `attempts=1`.
6. **Live readiness output was inspected directly**, e.g.
   `GET /health/ready` → `{"service":"api","status":"ok","version":"0.1.0","database":"ok"}`
   and `GET :8100/health/ready` → `{"service":"ai","status":"ok","version":"0.1.0","database":null}`.

## 4. Known limitations or notes

- The `503` path was verified by forcing the probe to fail in-process; a genuine
  database outage was not staged, because no PostgreSQL instance was reachable
  without a Docker daemon. The probe uses the real `Session.execute("SELECT 1")`
  path, and a connection-level `OperationalError` is what the handler catches.
- Readiness is a single synchronous probe with no timeout or caching. Every
  `/health/ready` call performs one database round trip. That is intentional for
  a starter: it is cheap, and it keeps the endpoint honest. A production system
  would add a probe timeout and possibly a short cache.
- Tests still use SQLite rather than PostgreSQL, so PostgreSQL-specific
  behaviour (for example timezone handling) remains uncovered.
- `Docker compose up` was not exercised in this environment; the local
  process-based run above is the substitute. `compose.yaml`, the `Dockerfile`,
  and the health checks in `compose.yaml` were not modified.

## 5. AI Use Statement

- **Tool name:** DeepSeek Harness (AI coding agent, deepseek-flash model).
- **What it was used for:** reading the assignment PDF; inspecting the starter
  repository; drafting the readiness-endpoint change and its tests; running the
  test suite, linter, migration, and a local end-to-end smoke run; drafting this
  summary and the Canvas note.
- **What I verified, changed, or rejected:**
  - I read every changed file and confirmed the behaviour against the live
    running services rather than trusting the generated summary.
  - I reviewed the `try`/`except SQLAlchemyError` scope and kept the status code
    on the `503` response explicit instead of accepting a broad catch-all.
  - I confirmed the never-collected test file was a real defect before deleting
    it, and checked that its unique test was recovered rather than dropped.
  - I rejected an early draft that raised a bare `RuntimeError` for the `503`
    test: it exercised dependency-injection failure (a `500`) rather than a
    failing database probe, so the test would not have covered the change.
  - I rejected widening the change to AI-service readiness dependencies and to
    the `compose.yaml` health checks; both were outside the intended scope of one
    small, reviewable change.
  - The final `pytest`, `ruff`, migration, and smoke commands were re-run after
    the last edit; the outputs quoted above are from those runs.
