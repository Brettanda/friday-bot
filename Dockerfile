# Temp Stage
# FROM python:3.11 AS build

# WORKDIR /usr/src/app

# RUN wget -nc -nc https://the-eye.eu/public/AI/models/nomic-ai/gpt4all/gpt4all-lora-quantized-ggml.bin -P /usr/src/app/models


# Final Stage
FROM python:3.12-slim

# https://stackoverflow.com/questions/68673221/warning-running-pip-as-the-root-user
ENV PIP_ROOT_USER_ACTION=ignore

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && apt-get install -y ffmpeg curl git

RUN --mount=type=cache,target=/root/.cache/pip \
  --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
  pip install --upgrade pip && pip install --requirement /tmp/requirements.txt

WORKDIR /usr/src/app

# COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

EXPOSE 4001
# EXPOSE 443
EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=5 \
  CMD curl -f http://localhost:443/version || exit 1

# Just in case https://hynek.me/articles/docker-signals/
STOPSIGNAL SIGINT

ENTRYPOINT python3 index.py db upgrade && exec python3 index.py