FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY ./app /app/app
COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM public.ecr.aws/docker/library/python:3.13-rc-slim-bookworm
# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Create app user
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Expose the port
EXPOSE 8080

# Copy the AWS Lambda Web Adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["fastapi", "run", "/app/app/main.py", "--proxy-headers", "--port", "8080", "--host", "0.0.0.0"]
