#!/bin/bash

echo "Apply database migrations"
# python manage.py migrate --fake
python manage.py migrate

echo "Collect static files"
python manage.py collectstatic --noinput

# Start server
echo "Starting server"
gunicorn champion_backend.asgi:application -w 9 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:80