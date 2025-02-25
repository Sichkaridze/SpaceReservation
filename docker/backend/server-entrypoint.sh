#!/bin/sh

until cd /app/backend
do
    echo "Waiting for Django application (server volume)..."
done

until python manage.py migrate
do
    echo "Waiting for database..."
    sleep 2
done

python manage.py collectstatic --noinput

# python manage.py createsuperuser --noinput

exec gunicorn --reload DjangoCore.wsgi --bind 0.0.0.0:8000 --workers 4 --threads 4

# for debug
#python manage.py runserver 0.0.0.0:8000
