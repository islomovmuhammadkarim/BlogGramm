FROM python:3.11-slim

WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=config.settings

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate && \
    python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from django.contrib.auth.models import User; User.objects.filter(username='mrton').exists() or User.objects.create_superuser('mrton','','admin123')" && \
    python bot_polling.py & \
    gunicorn config.wsgi --bind 0.0.0.0:$PORT
