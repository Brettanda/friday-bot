# syntax=docker/dockerfile:1

FROM python:3.8

WORKDIR /code

COPY requirements.txt .
# COPY install.sh .
# RUN ./install.sh
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

COPY . .

CMD ["python3", "./index.py"]