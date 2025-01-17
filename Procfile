web: gunicorn channelmoderation.wsgi --log-file -
worker: python moderation/bot.py
heroku config:set TORCH_CUDA=0