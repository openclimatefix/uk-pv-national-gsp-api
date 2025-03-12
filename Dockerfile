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
COPY nowcasting_api /app/nowcasting_api
COPY ./script /app/script

# pin coverage
RUN pip install -U coverage

# make sure 'nowcasting_api' is in python path - this is so imports work
ENV PYTHONPATH=${PYTHONPATH}:/app/nowcasting_api
