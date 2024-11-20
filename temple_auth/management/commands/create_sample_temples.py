from django.core.management.base import BaseCommand
from temple_auth.models import Temple


class Command(BaseCommand):
    help = 'Create predefined sample temples.'

    sample_temples = [
        {
            "temple_name": "ഓട്ടറാട്ട്-കാട്ടുകണ്ടത്തിൽ-പാലത്തിങ്കൽ ധർമ്മദൈവ ക്ഷേത്രം",
            "temple_place": "",
            'temple_short_name': 'ധർമ്മദൈവ ക്ഷേത്രം',
            "temple_bill_title": "ഓട്ടറാട്ട് കാട്ടുകണ്ടത്തിൽ പാലത്തിങ്കൽ ധർമ്മദൈവ ക്ഷേത്രം",
            "temple_bill_mid": "കാര",
            "temple_bill_footer": ""
        }
    ]

    def handle(self, *args, **kwargs):
        for temple_data in self.sample_temples:
            temple_name = temple_data["temple_name"]
            temple_place = temple_data["temple_place"]
            temple_short_name = temple_data["temple_short_name"]
            temple_bill_title = temple_data["temple_bill_title"]
            temple_bill_mid = temple_data["temple_bill_mid"]
            temple_bill_footer = temple_data["temple_bill_footer"]

            temple, created = Temple.objects.get_or_create(
                temple_name=temple_name,
                defaults={
                    "temple_place": temple_place,
                    "temple_short_name": temple_short_name,
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
