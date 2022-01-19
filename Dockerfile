FROM python:3.9-slim-buster

COPY . /app

WORKDIR /app

RUN export PYTHONPATH=$PYTHONPATH:./src

RUN pip install -r requirements.txt
