FROM python:3.8

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

EXPOSE 80

RUN chmod 755 /app/docker-startup.sh /app/docker-startup.prod.sh
