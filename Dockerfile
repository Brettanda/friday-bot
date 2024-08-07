# Temp Stage
FROM python:3.11 AS build

WORKDIR /usr/src/app

# RUN wget -nc -nc https://the-eye.eu/public/AI/models/nomic-ai/gpt4all/gpt4all-lora-quantized-ggml.bin -P /usr/src/app/models

COPY ./requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --upgrade pip && pip install -r requirements.txt

# Final Stage
FROM python:3.11-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && apt-get install -y ffmpeg

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && apt-get install -y curl

WORKDIR /usr/src/app

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

EXPOSE 4001
# EXPOSE 443
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD curl -f http://localhost:443/version || exit 1

# Just in case https://hynek.me/articles/docker-signals/
STOPSIGNAL SIGINT

ENTRYPOINT python3 index.py db upgrade && exec python3 index.py