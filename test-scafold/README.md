# test-scafold

This folder contains API tests that are run against a freshly generated scaffold app.

## Running locally

```sh
pytest test-scafold/tests
```

Every test runs once per backend: `[mongo]`, `[sqlite]` and `[postgres]`.

- Mongo uses an in-memory `mongod` (`APP_DB_URI=memory://`), downloaded on first run.
- SQLite uses `sqlite:///:memory:`.
- Postgres runs in a throwaway `postgres:16` Docker container started for the session on a random port, so Docker must be running. The container is removed when the session ends.

To run a single backend, set `APP_DB_BACKEND` (and optionally `APP_DB_URI`), e.g. `APP_DB_BACKEND=sqlite pytest test-scafold/tests`.

## CI

The GitHub Action installs the template CLI, runs `server-template new` into `test-scafold/app`, and then executes the tests in `test-scafold/tests` once per backend in a matrix, setting `APP_DB_BACKEND` and `APP_DB_URI` for each job.

`test-scafold/app` is generated at CI/runtime and should not be committed.
