FROM python:3.11 AS build

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /usr/src/app

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.9.0/wait /wait
RUN chmod +x /wait

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 4001
EXPOSE 5000

ENV WAIT_HOSTS="db:5432,lavalink:2333"

# Just in case https://hynek.me/articles/docker-signals/
STOPSIGNAL SIGINT

ENTRYPOINT /wait && python3 index.py db upgrade && exec python3 index.py