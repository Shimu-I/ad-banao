# Tests

- `unit/`: pure logic, fast, no web server or database needed.
- `integration/`: the API and database models. Need the packages in `backend/requirements-dev.txt`.
- `evaluation/`: the test ads with injected errors (goal S1).

Run everything from the repository root with `make test`.
