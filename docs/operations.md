# Operations Notes

## Local startup

1. copy `.env.example` to `.env`
2. run `docker compose up --build`
3. open the API docs if desired
4. submit a case through the API
5. confirm the worker processes the job

## Health endpoints

- API live: `/health/live`
- API ready: `/health/ready`
- AI live: `/health/live`
- AI ready: `/health/ready`

### What readiness means

`/health/live` answers "is the process running?" and never touches a dependency.

`/health/ready` answers "can this instance serve traffic?" The API version probes
its database with a trivial `SELECT 1`:

- probe succeeds: `200` with
  `{"service": "api", "status": "ok", "version": "0.1.0", "database": "ok"}`
- probe fails: `503` with
  `{"service": "api", "status": "unavailable", "error": "database"}`, and an
  error-level `readiness_check_failed` log line naming the dependency

The AI service is stateless, so its `/health/ready` reports `service`, `status`,
and `version` without a dependency field.

Both services read `version` from `SERVICE_VERSION` in
`services/common/config.py`, which is also the FastAPI `version`, so the reported
version only has to change in one place.

## Metrics

- API metrics: `/metrics`
- AI metrics: `/metrics`
- Prometheus: enable the `observability` profile

## Common useful commands

- run tests: `pytest -q`
- run unit and integration tests: `pytest -q tests/unit tests/integration`
- run smoke tests: `SMOKE_BASE_URL=http://localhost:8000 pytest tests/smoke -q`
- run migrations: `docker compose run --rm api alembic upgrade head`
- seed demo data: `docker compose run --rm api python scripts/seed_demo_data.py`

## Where tests put their scratch files

The `db_session` fixture builds a throwaway SQLite database per test under the
repository-local `.pytest_tmp/` directory (git-ignored) instead of the operating
system temp directory. Test runs therefore work on hosts whose OS temp location
is locked down, and any leaked test database is easy to find and delete.

## Failure handling in the starter

If AI processing fails:

- the job is marked failed
- the case is marked failed
- the error is recorded on the job row

## Resetting local state

To remove local database state:

- `docker compose down -v --remove-orphans`
