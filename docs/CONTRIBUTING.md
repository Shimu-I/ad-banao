# Contributing and workflow

This project is built one step at a time. Each step gets its own branch, is checked as far as possible, then merged.

## Branches

- The default branch always holds reviewed, working code.
- One branch per step, named `step-NN-short-name`, for example `step-04-generation`.
- Small fixes and documentation use `fix/short-name`, `docs/short-name` or `chore/short-name`.

## Commits

Use short, imperative messages with a type prefix:

- `feat:` new functionality
- `fix:` bug fix
- `docs:` documentation only
- `test:` tests only
- `chore:` setup, config, tooling

Example: `feat: add price normalization for BDT and USD formats`

## Pull requests

1. Open a pull request from the step branch into the default branch.
2. Describe what the step adds and what was tested.
3. State anything that could not be tested, for example parts that need packages or models not available in the build environment.
4. Update [PROGRESS.md](PROGRESS.md) in the same pull request: step status, tests run, and anything the project owner tested personally.
5. Merge after the checks pass, then pull the merged branch before starting the next step.

## Build steps

1. Repo setup
2. Backend skeleton and database models
3. Product and brand profiles
4. One-form brief and grounded generation (product description and ad text)
5. Ad design and image renderer (layers, templates, sizes)
6. Ad editing API (versions, undo, resize, change template)
7. Verification: prices and details
8. Verification: OCR
9. Verification: unsupported claims
10. Verification: brand and image integrity
11. Reports, one-click fixes, approval and export
12. Frontend: (a) guided form and generate, (b) ad editor, (c) check panel and export
13. Test set and evaluation
14. Deployment and docs

## Secrets

Never commit API keys or `.env`. Use `.env.example` to document required variables.
