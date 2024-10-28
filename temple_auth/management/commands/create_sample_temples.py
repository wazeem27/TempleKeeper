from django.core.management.base import BaseCommand
from temple_auth.models import Temple


class Command(BaseCommand):
    help = 'Create predefined sample temples.'

    sample_temples = [
        {
            "temple_name": "Shree Vishnu Temple",
            "temple_place": "Thrissur",
            "temple_bill_title": "Shree Vishnu Temple Billing",
            "temple_bill_mid": "Welcome to Shree Vishnu Temple",
            "temple_bill_footer": "Thank you for your donation!",
        },
        {
            "temple_name": "Shree Durga Temple",
            "temple_place": "Kochi",
            "temple_bill_title": "Shree Durga Temple Billing",
            "temple_bill_mid": "Welcome to Shree Durga Temple",
            "temple_bill_footer": "Thank you for your support!",
        },
        {
            "temple_name": "Shree Shiva Temple",
            "temple_place": "Kottayam",
            "temple_bill_title": "Shree Shiva Temple Billing",
            "temple_bill_mid": "Welcome to Shree Shiva Temple",
            "temple_bill_footer": "Thank you for visiting!",
        },
    ]

    def handle(self, *args, **kwargs):
        for temple_data in self.sample_temples:
            temple_name = temple_data["temple_name"]
            temple_place = temple_data["temple_place"]
            temple_bill_title = temple_data["temple_bill_title"]
            temple_bill_mid = temple_data["temple_bill_mid"]
            temple_bill_footer = temple_data["temple_bill_footer"]

            temple, created = Temple.objects.get_or_create(
                temple_name=temple_name,
                defaults={
                    "temple_place": temple_place,
                    "temple_bill_title": temple_bill_title,
                    "temple_bill_mid": temple_bill_mid,
                    "temple_bill_footer": temple_bill_footer,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Temple "{temple_name}" created successfully.'))
            else:
                self.stdout.write(self.style.WARNING(f'Temple "{temple_name}" already exists.'))

        self.stdout.write(self.style.SUCCESS('Finished creating sample temples.'))
