FROM python:3.13
LABEL authors="dima.sichkar2003@gmail.com"

ENV PYTHONUNBUFFERED=1

RUN apt update && apt install -y libpq-dev gcc python3-dev

#RUN pip install --no-cache-dir -r requirements.txt # запобігає збереженню кешу встановлених пакетів, що може зменшити розмір контейнера.
RUN pip install --upgrade pip
RUN pip install gunicorn
ADD ./requirements.txt /app/
RUN pip install -r /app/requirements.txt

ADD ./src /app/backend
ADD ./docker /app/docker

RUN chmod +x /app/docker/backend/server-entrypoint.sh
RUN chmod +x /app/docker/backend/worker-entrypoint.sh
