web: gunicorn solarmonitor.app:create_app\(\) -b 0.0.0.0:$PORT -w 3 --preload
worker: celery worker --app=solarmonitor.app
clock: python clock.py
