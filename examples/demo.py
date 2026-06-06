"""pylog — Universal Structured Logger Demo.

Demonstrates every feature of the pylog library.
"""

from __future__ import annotations

import asyncio
import logging
import sys

# Add src to path for demo
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

import pylog
from pylog import (
    Config,
    Format,
    LoggingMiddleware,
    log_db_query,
    log_request,
    log_response,
    log_service_debug,
    log_service_error,
    log_success,
    get_context_logger,
    set_context_logger,
)


def main() -> None:
    # ──────────────────────────────────────────
    # 1. Initialize the logger
    # ──────────────────────────────────────────
    app = pylog.new(Config(
        level=pylog.TRACE,
        fmt=Format.PRETTY,
        caller=True,
        output=sys.stdout,
    ))

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              Pylog Logger — Format Showcase                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # ──────────────────────────────────────────
    # 2. Basic log levels
    # ──────────────────────────────────────────
    print_section("Basic Log Levels")

    app.trace("This is a TRACE message — finest granularity")
    app.debug("This is a DEBUG message — diagnostic detail")
    app.info("This is an INFO message — normal operation")
    app.warn("This is a WARN message — something looks off")
    app.error("This is an ERROR message — something failed")

    # ──────────────────────────────────────────
    # 3. Structured fields
    # ──────────────────────────────────────────
    print_section("Structured Fields")

    app.info("User authentication successful",
        user="baleeghu", action="login", ip="192.168.1.42", attempt=1, mfa=True)

    app.debug("Query plan analyzed",
        query="SELECT * FROM users WHERE active = true", params=0, cost_estimate=0.0034)

    # ──────────────────────────────────────────
    # 4. Error logging with context
    # ──────────────────────────────────────────
    print_section("Error Logging")

    app.error("Failed to connect to database",
        error="connection refused: dial tcp 10.0.0.5:5432",
        host="10.0.0.5", port=5432, database="myapp_prod")

    app.error("Service operation failed",
        error="user service: repository: connection refused",
        operation="GetUserByID", user_id="usr_abc123")

    # ──────────────────────────────────────────
    # 5. Sub-loggers with context
    # ──────────────────────────────────────────
    print_section("Sub-loggers (Component / Request Scoped)")

    db_logger = app.with_component("database")
    db_logger.info("Connection pool initialized", driver="pgx", host="localhost:5432")
    db_logger.debug("Pool stats", pool_size=25, idle=10)

    auth_logger = app.with_component("auth")
    auth_logger.info("Auth provider configured", provider="kerberos")

    req_logger = app.with_request_id("req-7f3a-4b2c-9d1e")
    req_logger.info("Processing request", method="POST", path="/api/v1/entries")
    req_logger.debug("Request body parsed", content_type="application/json", body_size=1024)

    trace_logger = app.with_trace_id("trace-abc123def456")
    trace_logger.info("Distributed trace started")

    # ──────────────────────────────────────────
    # 6. Context integration
    # ──────────────────────────────────────────
    print_section("Context-based Logging")

    token = set_context_logger(req_logger)
    l = get_context_logger()
    l.info("Handler retrieved logger from context")
    l.debug("Validating request payload", step="validation")
    l.info("Processing complete", step="processing", elapsed_ms=42)
    token.var.reset(token)

    # ──────────────────────────────────────────
    # 7. Helper functions
    # ──────────────────────────────────────────
    print_section("Helper Functions")

    log_success(app, "Database migration completed")

    log_request(app, "GET", "/api/v1/users/42", "baleeghu")
    log_request(app, "POST", "/api/v1/entries", "servicebot")

    log_response(app, "GET", "/api/v1/users/42", 200, 12.0)
    log_response(app, "POST", "/api/v1/entries", 201, 45.0)
    log_response(app, "GET", "/api/v1/secrets", 403, 2.0, error="insufficient permissions")
    log_response(app, "GET", "/api/v1/missing", 404, 1.0, error="resource not found")
    log_response(app, "POST", "/api/v1/entries", 500, 3000.0, error="deadlock detected")

    log_db_query(app, "SELECT", "users", 3.0, rows_affected=42)
    log_db_query(app, "INSERT", "time_entries", 15.0, rows_affected=1)
    log_db_query(app, "DELETE", "old_sessions", 200.0, rows_affected=1337)

    log_service_error(app, "UserService", "CreateUser", "duplicate email", fields={
        "email": "user@example.com",
        "provider": "internal",
    })

    log_service_debug(app, "CacheService", "Get", "Cache lookup completed", fields={
        "key": "user:42:profile",
        "hit": True,
        "ttl_ms": 45000,
    })

    # ──────────────────────────────────────────
    # 8. Redaction
    # ──────────────────────────────────────────
    print_section("Sensitive Field Redaction")

    app.info("Login attempt with redacted credentials",
        username="baleeghu",
        password="super_secret_pass_123",
        api_key="sk-proj-abc123def456ghi789",
        email="user@deshaw.com")

    form_data = {
        "username": "baleeghu",
        "password": "hunter2",
        "access_token": "eyJhbGciOiJIUzI1NiJ9",
        "action": "login",
    }
    redacted = pylog.redact_map(form_data)
    app.info("Form submission (redacted)", form_data=redacted)

    # ──────────────────────────────────────────
    # 9. ASGI middleware
    # ──────────────────────────────────────────
    print_section("ASGI Middleware (simulated requests)")

    async def demo_app(scope, receive, send):
        l = get_context_logger()
        l.info("Processing request inside handler")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    mw_logger = pylog.new(Config(fmt=Format.PRETTY, output=sys.stdout))
    mw = LoggingMiddleware(demo_app, mw_logger)

    async def noop_send(msg):
        pass

    scope = {"type": "http", "method": "GET", "path": "/api/health", "headers": []}
    asyncio.run(mw(scope, None, noop_send))
    print()

    scope2 = {
        "type": "http", "method": "POST", "path": "/api/data",
        "headers": [(b"x-request-id", b"custom-req-id")],
    }
    asyncio.run(mw(scope2, None, noop_send))

    # ──────────────────────────────────────────
    # 10. JSON output mode
    # ──────────────────────────────────────────
    print_section("JSON Output Mode (for production / log aggregators)")

    json_logger = pylog.new(Config(
        fmt=Format.JSON,
        caller=True,
        output=sys.stdout,
    ))

    json_logger.info("Application started", environment="production", version="2.4.1")
    json_logger.error("Cache unavailable", error="connection timeout", service="redis", host="redis.internal:6379")

    # ──────────────────────────────────────────
    # Done!
    # ──────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    All formats demonstrated!                 ║")
    print("╚══════════════════════════════════════════════════════════════╝")


def print_section(title: str) -> None:
    pad = 58 - len(title)
    if pad < 0:
        pad = 0
    print()
    print(f"── {title} {'─' * pad}")
    print()


if __name__ == "__main__":
    main()
