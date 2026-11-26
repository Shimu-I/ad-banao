# API conventions: request ids, errors, logs and AI settings

What every part of the API does the same way (goal F8). Written for whoever reads a failing page or a server log.

## Request id

Every answer carries an `X-Request-ID` header. If a caller sends a safe id (8 to 64 letters, digits, `.`, `_`, `-`) it is kept, so a page and the server can share one id; otherwise a new one is made. The page can read the header (it is listed in CORS `expose_headers`). The same id is on every log line for that request and inside every error body.

## One error format

Every failure, whatever its cause, has the same three fields:

```json
{"detail": "An account with this email already exists.", "code": "conflict", "request_id": "3f1c9a..."}
```

| Field | Meaning |
| --- | --- |
| `detail` | The message for a person, or the list of problems (validation, price checks). Unchanged from before, so existing pages keep working |
| `code` | Short stable name for programs: `not_signed_in` (401), `forbidden` (403), `not_found` (404), `conflict` (409), `validation_error` (422 from the schema), `rate_limited` (429), `unavailable` (503), `internal_error` (500). A route that already names its problem (`not_an_image`, `missing_price`) keeps that name |
| `request_id` | Same as the `X-Request-ID` header. Quote it when asking for help |

An unexpected error (a bug) returns `500` with `internal_error` and a generic message. The cause and the stack trace go to the log with the request id, never to the client.

## Logs

One line per event, with the request id. Each request also writes an access line: method, path (no query string, because it can hold private values), status and time in milliseconds.

| Setting | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_JSON` | `false` | `true` prints one JSON object per line, for a log service (use online) |

## Health checks

| URL | Answers |
| --- | --- |
| `GET /health` | The API is up, and which environment |
| `GET /health/db` | The database answers (503 if not, with no connection details) |
| `GET /health/providers` | Which AI services have a key and which model name each uses. Nothing is called and no key is shown |

## AI settings

Model names are settings because providers retire models: `gemini-2.0-flash` (the old default) was shut down on 2026-06-01. Keys stay empty until the owner adds them.

| Setting | Default | Checked |
| --- | --- | --- |
| `GEMINI_API_KEY` | empty | |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Google's deprecation page (updated 2026-10-22) names it, with `gemini-3.8-flash`, as the models to use for new projects. **Not yet tried with a real key.** Forum reports say some older models stopped answering before their announced shutdown date, so change this setting first if a call fails |
| `GROQ_API_KEY` | empty | |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | **Not re-checked** against Groq's current list. Change it if a call fails |

Without a working provider the text comes from the built-in template (source `basic`), as before.

## Still to do in F8

The `/api/v1` path prefix. It changes every address the pages and scripts call, so it is its own pull request.
