#!/bin/bash

echo "Apply database migrations"
# python manage.py migrate --fake
python manage.py migrate

echo "Collect static files"
python manage.py collectstatic --noinput

# Start server
echo "Starting server"
uvicorn django_app.asgi:application --reload --host 0.0.0.0 --port 80