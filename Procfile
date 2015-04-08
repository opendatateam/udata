web: python manage.py serve -d -r -h 0.0.0.0 -p 6666
worker: celery -A udata.worker worker
beat: celery -A udata.worker beat
