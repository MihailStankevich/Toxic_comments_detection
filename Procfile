release: pip install -r runtime-requirements.txt
web: gunicorn channelmoderation.wsgi --log-file -
worker: python moderation/bot.py
