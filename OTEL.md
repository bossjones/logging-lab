> if I have a fastapi app, what env vars do I need to set to send traces, metrics, and logs to an instance of this demo ?

⏺ Looking at the demo's OTel Collector configuration, here's what you need:

  Environment Variables for FastAPI

  # Required
  OTEL_SERVICE_NAME=your-fastapi-app
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  # HTTP endpoint

  # Enable all signals
  OTEL_TRACES_EXPORTER=otlp
  OTEL_METRICS_EXPORTER=otlp
  OTEL_LOGS_EXPORTER=otlp

  # Optional but recommended
  OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  OTEL_RESOURCE_ATTRIBUTES=service.namespace=opentelemetry-demo
  OTEL_PYTHON_LOG_CORRELATION=true
  OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative

  Important: Expose Collector Ports

  The demo's docker-compose doesn't expose fixed host ports for the collector. Add to .env.override:

  # Or modify docker-compose.yml otel-collector ports section to:
  # - "4317:4317"  # gRPC
  # - "4318:4318"  # HTTP

  Or create a docker-compose.override.yml:
  services:
    otel-collector:
      ports:
        - "4317:4317"
        - "4318:4318"

  Python Dependencies

  pip install opentelemetry-distro opentelemetry-exporter-otlp
  opentelemetry-bootstrap -a install  # Auto-install instrumentations

  Running Your App

  # With auto-instrumentation (recommended)
  opentelemetry-instrument python -m uvicorn main:app --host 0.0.0.0 --port 8000

  # Or if instrumenting manually, just run normally
  python -m uvicorn main:app --host 0.0.0.0 --port 8000

  Alternative: Run Inside Docker Network

  If your FastAPI app runs in the same Docker network (opentelemetry-demo), use:

  OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317  # gRPC
  # or
  OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318  # HTTP

  Add to your docker-compose:
  networks:
    default:
      name: opentelemetry-demo
      external: true