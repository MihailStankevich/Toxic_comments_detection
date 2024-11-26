# moderation/management/commands/run_bot.py
from django.core.management.base import BaseCommand
from moderation.bot import main  # Import the main function from bot.py

class Command(BaseCommand):
    help = 'Run the Telegram bot'

    def handle(self, *args, **kwargs):
        import asyncio
        asyncio.run(main())  # Run the main function