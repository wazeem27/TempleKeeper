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
            ("ഗണപതി ഹോമം", 50.00),
            ("ഒരുദിവസത്തെ പൂജ", 1200.00),
            ("പുഷ്‌പാഞ്ജലി", 10.00),
            ("മഞ്ഞൾപ്പൊടി", 20.00),
            ("പനിനീർ അഭിഷേകം", 30.00),
            ("അഭിഷേകങ്ങൾ (കൊണ്ടുവരണം)", 10.00),
            ("ശാക്തേയ പുഷ്‌പാഞ്ജലി", 30.00),
            ("ഐക്യമത്യ പുഷ്‌പാഞ്ജലി", 30.00),
            ("വിദ്യാമന്ത്ര പുഷ്‌പാഞ്ജലി", 30.00),
            ("ശത്രുസംഹാര പുഷ്‌പാഞ്ജലി", 30.00),
            ("ശ്രീസൂക്ത പുഷ്‌പാഞ്ജലി", 30.00),
            ("പുരുഷസൂക്ത പുഷ്‌പാഞ്ജലി", 30.00),
            ("മംഗല്യസൂക്ത പുഷ്‌പ ഞ്ജലി", 30.00),
            ("ഭാഗ്യസൂക്ത പുഷ്‌പാ ജലി", 30.00),
            ("സ്വയംവര പുഷ്‌പാഞ്ജലി", 30.00),
            ("കുടുംബ പുഷ്‌പാഞ്ജലി", 100.00),
            ("ഗുരുതി", 50.00),
            ("മുത്തപ്പന് മുറുക്കാൻ", 50.00),
            ("വിഷ്ണുമായക്ക് മുറുക്കാൻ", 50.00),
            ("എണ്ണ വലുത്", 100.00),
            ("എണ്ണ ചെറുത്", 50.00),
            ("കടുംപായസം", 60.00),
            

            ("ശർക്കര പായസം", 60.00),
            ("പാൽപായസം", 60.00),
            ("പാലും നൂറും", 100.00),
            ("പട്ടും താലിയും", 100.00),
            ("രക്ഷസിന് പൂജ", 100.00),
            ("നാഗപൂജ", 100.00),
            ("മുരുകന് പൂജ", 100.00),
            ("നടയ്ക്കൽ പറ", 100.00),
            ("കട്യാവ്", 150.00),

            ("മുത്തപ്പന് പൊടികലശം", 100.00),
            ("വിഷ്ണുമായസ്വാമിക്ക് കലശം", 250.00),
            ("കരിംകുട്ടിസ്വാമിക്ക് കലശം", 100.00),
            ("ഭഗവതി സേവ", 250.00),
            ("മറുത മുത്തിയ്ക്ക് പിടി വഴിപാട്", 100.00),
            ("നെയ്യ് വിളക്ക്", 20.00),
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
                    order=added_count,
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