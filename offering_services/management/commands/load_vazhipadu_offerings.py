import logging
from django.core.management.base import BaseCommand
from temple_auth.models import Temple
from offering_services.models import VazhipaduOffering

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load predefined Vazhipadu offerings into the VazhipaduOffering model'

    def handle(self, *args, **kwargs):
        # List of Vazhipadu offerings to be inserted (name, price)
        vazhipadu_offerings = [
            ("നാരായണ സേവ", 500.00),
            ("അഭിഷേകം", 300.00),
            ("അർച്ചന", 100.00),
            ("പൂജ", 200.00),
            ("വേദചന്തനം", 150.00),
            ("കുമ്പാഭിഷേകം", 1000.00),
            ("സഹസ്രനാമാർച്ചന", 800.00),
            ("തിരുമഞ്ജനം", 600.00),
            # Add more offerings as needed
        ]

        # Initialize a counter for the number of offerings added
        added_count = 0

        for name, price in vazhipadu_offerings:
            try:
                # Use get_or_create to avoid duplicates
                offering, created = VazhipaduOffering.objects.get_or_create(
                    temple=Temple.objects.first(),
                    name=name,
                    description="",
                    defaults={'price': price}
                )

                if created:
                    logger.info(f"Added Vazhipadu offering: {name} (Price: {price})")
                    added_count += 1
                else:
                    logger.info(f"Vazhipadu offering already exists: {name}")

            except Exception as e:
                logger.error(f"Error adding Vazhipadu offering '{name}': {e}")

        # Output results
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {added_count} Vazhipadu offerings into the database!'))
        logger.info(f'Total Vazhipadu offerings added: {added_count}')