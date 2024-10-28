import logging
from temple_auth.models import Temple
from django.core.management.base import BaseCommand
from temple_inventory.models import InventoryItem

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load predefined inventory items into the InventoryItem model'

    def handle(self, *args, **kwargs):
        # List of inventory items to be inserted (name, price, count)
        inventory_items = [
            ("തേങ്ങ", 20.00, 100),
            ("പൂക്കള്", 10.00, 200),
            ("ആഗരം", 5.00, 150),
            ("പഴങ്ങൾ", 30.00, 50),
            ("പലഹാരം", 15.00, 75),
            ("അരിപ്പൊടി", 50.00, 30),
            ("നെയ്യ്", 100.00, 20),
            ("എണ്ണ", 80.00, 25),
            # Add more items as needed
        ]

        # Initialize a counter for the number of items added
        added_count = 0
        
        for name, price, count in inventory_items:
            try:
                # Use get_or_create to avoid duplicates
                item, created = InventoryItem.objects.get_or_create(
                    temple=Temple.objects.first()
                    name=name,
                    description="",
                    defaults={'price': price, 'count': count}
                )

                if created:
                    logger.info(f"Added inventory item: {name} (Price: {price}, Count: {count})")
                    added_count += 1
                else:
                    logger.info(f"Inventory item already exists: {name}")

            except Exception as e:
                logger.error(f"Error adding inventory item '{name}': {e}")

        # Output results
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {added_count} inventory items into the database!'))
        logger.info(f'Total inventory items added: {added_count}')