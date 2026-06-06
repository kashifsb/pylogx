# pylog

![Python CI](https://github.com/kashifsb/pylogx/actions/workflows/ci.yml/badge.svg)

Universal structured logging library for Python — stdlib-only, Python 3.10+.

## Features

- **Leveled logging** — Trace, Debug, Info, Warn, Error, Fatal
- **Pretty + JSON output** — colored human-readable or structured JSON
- **Auto-detection** — TTY gets pretty mode, non-TTY gets JSON
- **Environment configuration** — LOG_LEVEL, LOG_FORMAT, LOG_CALLER, NO_COLOR, TERM
- **Sub-loggers** — persistent fields via with_component, with_request_id, with_trace_id
- **Field redaction** — auto-detect and mask sensitive keys (passwords, tokens, API keys)
- **ASGI middleware** — request/response logging with auto-generated request IDs
- **Context integration** — store/retrieve loggers from `contextvars`
- **Convenience helpers** — log_success, log_request, log_response, log_db_query, log_service_error, log_service_debug
- **Thread-safe** — safe for concurrent use

## Quick Start

```bash
pip install -e .
```

```python
import pylog

logger = pylog.init_from_env()

logger.info("User authenticated", user="alice", attempt=1)
```

## Configuration

| Environment Variable | Values | Default |
|---------------------|--------|---------|
| `LOG_LEVEL` | trace, debug, info, warn, error, fatal | info |
| `LOG_FORMAT` | pretty, json, auto | auto (TTY=pretty, else JSON) |
| `LOG_CALLER` | true, 1 | disabled |
| `NO_COLOR` | (any value) | unset |
| `TERM` | dumb (disables color) | unset |

Programmatic configuration via `Config`:

```python
import sys
import pylog
from pylog import Config, Format, new

logger = new(Config(
    level=pylog.TRACE,
    fmt=Format.PRETTY,
    caller=True,
    no_color=False,
    output=sys.stdout,  # defaults to sys.stderr
))
```

## Output Formats

### Pretty Mode (TTY)

```
2026/03/29 14:30:42 UTC INF User authenticated user=alice attempt=1 (demo.py:52)
2026/03/29 14:30:42 UTC ERR Connection failed error=timeout host=db.internal (demo.py:55)
```

### JSON Mode (production)

```json
{"level":"info","time":"2026-03-29T14:30:42Z","message":"User authenticated","user":"alice","attempt":1,"caller":"demo.py:52"}
{"level":"error","time":"2026-03-29T14:30:42Z","message":"Connection failed","error":"timeout","host":"db.internal","caller":"demo.py:55"}
```

## Structured Fields

Fields are passed as keyword arguments:

```python
logger.info("User authentication successful",
    user="baleeghu", action="login", ip="192.168.1.42", attempt=1, mfa=True)

logger.debug("Query plan analyzed",
    query="SELECT * FROM users WHERE active = true", params=0, cost_estimate=0.0034)

logger.error("Failed to connect to database",
    error="connection refused: dial tcp 10.0.0.5:5432",
    host="10.0.0.5", port=5432, database="myapp_prod")
```

## Sub-loggers

Create child loggers with persistent fields that appear on every log entry:

```python
db_logger = logger.with_component("database")
db_logger.info("Connection pool initialized", driver="pgx", host="localhost:5432")
db_logger.debug("Pool stats", pool_size=25, idle=10)

req_logger = logger.with_request_id("req-7f3a-4b2c-9d1e")
req_logger.info("Processing request", method="POST", path="/api/v1/entries")
req_logger.debug("Request body parsed", content_type="application/json", body_size=1024)

trace_logger = logger.with_trace_id("trace-abc123def456")
trace_logger.info("Distributed trace started")

# Arbitrary field:
custom = logger.with_field("version", "2.1")
```

## Context Integration

Store and retrieve loggers using `contextvars` (works with async code):

```python
from pylog import set_context_logger, get_context_logger

# Store a logger in the current context
req_logger = logger.with_request_id("req-7f3a-4b2c-9d1e")
token = set_context_logger(req_logger)

# Retrieve it anywhere in the same context
l = get_context_logger()
l.info("Handler retrieved logger from context")
l.debug("Validating request payload", step="validation")
l.info("Processing complete", step="processing", elapsed_ms=42)

# Reset context when done (optional)
token.var.reset(token)
```

`get_context_logger()` falls back to the global logger if none is stored in the context.

## Convenience Helpers

```python
from pylog import (
    log_success, log_request, log_response,
    log_db_query, log_service_error, log_service_debug,
)

log_success(logger, "Database migration completed")

log_request(logger, "GET", "/api/v1/users/42", "baleeghu")
log_request(logger, "POST", "/api/v1/entries", "servicebot")

log_response(logger, "GET", "/api/v1/users/42", 200, 12.0)
log_response(logger, "GET", "/api/v1/secrets", 403, 2.0, error="insufficient permissions")
log_response(logger, "POST", "/api/v1/entries", 500, 3000.0, error="deadlock detected")

log_db_query(logger, "SELECT", "users", 3.0, rows_affected=42)
log_db_query(logger, "INSERT", "time_entries", 15.0, rows_affected=1)

log_service_error(logger, "UserService", "CreateUser", "duplicate email", fields={
    "email": "user@example.com",
    "provider": "internal",
})

log_service_debug(logger, "CacheService", "Get", "Cache lookup completed", fields={
    "key": "user:42:profile",
    "hit": True,
    "ttl_ms": 45000,
})
```

`log_response` sets the level based on status code: 5xx = Error, 4xx = Warn, else Info.

## Field Redaction

Sensitive keys are automatically detected (case-insensitive, substring match):

`password`, `secret`, `token`, `access_token`, `refresh_token`, `authorization`, `api_key`, `apikey`, `api-key`, `credit_card`, `ssn`

| Input | redact_value Output |
|-------|-------------------|
| `""` | `****` |
| `"ab"` | `**` |
| `"secret"` | `s*****` |
| `"sk-proj-abc123"` | `s*************3` |

Sensitive fields are auto-redacted when passed as kwargs to log methods:

```python
# These fields are automatically redacted in the output
logger.info("Login attempt with redacted credentials",
    username="baleeghu",
    password="super_secret_pass_123",
    api_key="sk-proj-abc123def456ghi789",
    email="user@example.com")
```

Standalone redaction utilities:

```python
from pylog import is_sensitive_key, redact_value, redact_map, redact_headers

# Redact a map
redacted = redact_map({
    "username": "baleeghu",
    "password": "hunter2",
    "access_token": "eyJhbGciOiJIUzI1NiJ9",
    "action": "login",
})
logger.info("Form submission (redacted)", form_data=redacted)

# Redact HTTP headers
safe = redact_headers({
    "content-type": ["application/json"],
    "authorization": ["Bearer eyJ..."],
    "x-api-key": ["sk-live-abcdef123456"],
})
```

## HTTP Middleware (ASGI)

```python
from pylog import LoggingMiddleware, get_context_logger

# Direct ASGI usage
async def my_app(scope, receive, send):
    l = get_context_logger()  # Has request_id field
    l.info("Processing request inside handler")
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"OK"})

mw = LoggingMiddleware(my_app, logger)

# Or with Starlette/FastAPI
from starlette.applications import Starlette
app = Starlette()
app.add_middleware(LoggingMiddleware, logger=logger)
```

The middleware:
1. Extracts or generates `X-Request-ID` (UUID v4 if missing)
2. Creates a sub-logger with request_id, method, path
3. Logs request at Info level
4. Stores the logger in contextvars (retrieve via `get_context_logger()`)
5. Logs response with status and duration (5xx = Error, 4xx = Warn, else Info)

## Development

```bash
make install   # pip install -e ".[dev]"
make test      # python -m pytest tests/ -v
make example   # python examples/demo.py
make clean     # remove build artifacts
```

## Project Structure

```
pylog/
├── pyproject.toml
├── Makefile
├── examples/
│   └── demo.py                  # Comprehensive usage demo
├── src/pylog/
│   ├── __init__.py              # Public API exports
│   ├── logger.py                # Logger, Config, Format, TRACE, factory functions
│   ├── pretty.py                # PrettyFormatter (colored output)
│   ├── helpers.py               # Context helpers, log_success, log_request, etc.
│   ├── redact.py                # Sensitive key detection and masking
│   └── middleware.py            # ASGI LoggingMiddleware
└── tests/
    ├── test_logger.py
    ├── test_helpers.py
    ├── test_middleware.py
    └── test_redact.py
```
