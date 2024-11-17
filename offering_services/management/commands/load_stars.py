import logging
from django.core.management.base import BaseCommand
from offering_services.models import Star


# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load traditional star names into the Star model'

    def handle(self, *args, **kwargs):
        # List of traditional star names to be inserted
        stars = [
            "അശ്വതി",
            "ഭരണി",
            "കാർത്തിക",
            "രോഹിണി",
            "മകയിരം",
            "തിരുവാതിര",

            "പുണർതം",
            "പൂയം",
            "ആയില്യം",
            "മകം",
            "പൂരം",

            "ഉത്രം",
            "അത്തം",
            "ചിത്തിര",

            "ചോതി",
            "വിശാഖം",
            "അനിഴം",

            "തൃക്കേട്ട",
            "മൂലം",
            "പൂരാടം",
            "ഉത്രാടം",
            "തിരുവോണം",
            "അവിട്ടം",
            "ചതയം",
            "പൂരുരുട്ടാതി",
            "ഉത്രട്ടാതി",
            "രേവതി",
            # Add more stars as needed
        ]

        # Initialize a counter for the number of stars added
        added_count = 0
        
        for star_name in stars:
            try:
                # Use get_or_create to avoid duplicates
                star, created = Star.objects.get_or_create(name=star_name, description="")

                if created:
                    logger.info(f"Added star: {star_name}")
                    added_count += 1
                else:
                    logger.info(f"Star already exists: {star_name}")

            except Exception as e:
                logger.error(f"Error adding star '{star_name}': {e}")

        # Output results
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {added_count} star names into the database!'))
        logger.info(f'Total stars added: {added_count}')
