FROM python:3.12-slim

# copy files requirements
COPY ./requirements.txt /app/requirements.txt

# install requirements
RUN apt-get clean
RUN apt-get update -y
RUN pip install -U pip
RUN pip install -r /app/requirements.txt

# set working directory
WORKDIR /app

# copy files over
COPY ./src /app/src
COPY ./script /app/script

# pin coverage
RUN pip install -U coverage

# make sure 'src' is in python path - this is so imports work
ENV PYTHONPATH=${PYTHONPATH}:/app/src
