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
            "ആശ്വിനി",
            "ഭരണി",
            "കൃതിക",
            "റോഹിണി",
            "മൃഗശിര",
            "ആർദ്ര",
            "പുനർവാസു",
            "പുഷ്യം",
            "ആശ്ലേഷ",
            "മകം",
            "പൂർവ്വ ഫല്ഗുണി",
            "ഉത്തര ഫല്ഗുണി ",
            "ഹസ്തം",
            "ചിത്ര",
            "സ്വാതി",
            "വിശാഖം",
            "അനുരാധ",
            "ജ്യേഷ്ഠ",
            "മൂലം",
            "പൂർവ്വാശാഢ",
            "ഉത്തരാശാഢ",
            "തിരുവോണം",
            "അവിട്ടം",
            "ചതയം",
            "പൂർവ്വ ഭദ്രപാദം",
            "ഉത്തര ഭദ്രപാദം",
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
