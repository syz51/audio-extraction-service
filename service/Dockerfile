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

# --- FFmpeg static binary stage ---
FROM alpine:3.19 AS ffmpeg
# Install minimal tools and download the static build
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache curl xz \
    && curl -L -o /tmp/ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && mkdir -p /ffmpeg \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /ffmpeg --strip-components=1 \
    && rm /tmp/ffmpeg.tar.xz

FROM public.ecr.aws/docker/library/python:3.13-rc-slim-bookworm
# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Create app user
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app
USER app

# Copy the AWS Lambda Web Adapter and ffmpeg
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 --chown=app:app /lambda-adapter /opt/extensions/lambda-adapter

# Copy ffmpeg binaries into the runtime image
COPY --from=ffmpeg --chown=app:app /ffmpeg/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg --chown=app:app /ffmpeg/ffprobe /usr/local/bin/ffprobe

COPY --from=builder --chown=app:app /app /app

# Run the application
CMD ["fastapi", "run", "/app/app/main.py", "--proxy-headers", "--port", "8080", "--host", "0.0.0.0"]
