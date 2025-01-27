release: pip install -r runtime-requirements.txt
web: PYTHONPATH=/tmp gunicorn channelmoderation.wsgi --log-file -
worker: PYTHONPATH=/tmp python moderation/bot.py
