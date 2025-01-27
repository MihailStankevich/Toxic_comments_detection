web: pip install -r runtime-requirements.txt && gunicorn channelmoderation.wsgi --log-file -
worker: pip install -r runtime-requirements.txt && python moderation/bot.py
