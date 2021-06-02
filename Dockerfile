# syntax=docker/dockerfile:1

FROM python:3.8

WORKDIR /code

COPY requirements.txt .
COPY install.sh .
RUN ./install.sh
# RUN pip install -r requirements.txt

COPY . .

CMD ["python", "./index.py"]