# logging-lab

A Python lab for experimenting with modern structured logging and distributed tracing.

## Features

- **Structured logging** with [structlog](https://www.structlog.org/) - JSON or colored console output
- **Distributed tracing** with [OpenTelemetry](https://opentelemetry.io/) - trace context propagation
- **Request correlation** with [asgi-correlation-id](https://github.com/snok/asgi-correlation-id)
- **Non-blocking I/O** via QueueHandler/QueueListener for async performance
- **FastAPI** demo application with instrumented endpoints

## Quick Start

```bash
# Install dependencies
make install

# Start the server
make serve

# Or with OpenTelemetry auto-instrumentation
make serve-otel
```

The API will be available at `http://localhost:5002`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Hello World response |
| `GET /ping` | Health check |
| `GET /items/{item_id}` | Item lookup with optional query param |
| `GET /invalid` | Raises ValueError (error handling demo) |
| `GET /exception` | OpenTelemetry span exception recording demo |
| `GET /external-api` | External HTTP call to httpbin.org |

## Development

```bash
# Run linting and type checking
make lint

# Run tests
make test

# Run both
make
```

## Load Testing

```bash
# Headless mode (10 users, 1 spawn rate)
make locust

# With web UI
make locust-ui
```

## Architecture

```
src/logging_lab/
├── app.py            # FastAPI application with endpoints
├── logging_config.py # Structlog + stdlib logging configuration
├── middleware.py     # Access log middleware
└── telemetry.py      # OpenTelemetry tracer setup
```

### Logging Architecture

- **Structlog** serves as the frontend API with context propagation
- **Python stdlib logging** as backend with QueueHandler for non-blocking I/O
- **ProcessorFormatter** unifies both structlog and library logs (Uvicorn, etc.)
- Logs include `trace_id`, `span_id`, and `request_id` for correlation

## Project Docs

- [installation.md](installation.md) - Installing uv and Python
- [development.md](development.md) - Development workflows
- [publishing.md](publishing.md) - Publishing to PyPI

---

*Built from [simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
