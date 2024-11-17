from django.core.management.base import BaseCommand
from temple_auth.models import Temple


class Command(BaseCommand):
    help = 'Create predefined sample temples.'

    sample_temples = [
        {
            "temple_name": "ശ്രീ വിഷ്ണു ക്ഷേത്രം",
            "temple_place": "ഇരിഞ്ഞാലക്കുട",
            "temple_bill_title": "ശ്രീ വിഷ്ണു ക്ഷേത്രം",
            "temple_bill_mid": "തൃശ്ശൂർ",
            "temple_bill_footer": "ഓം വിഘ്‌നേശ്വരായ നമഃ"
        },
        {
            "temple_name": "ശ്രീ ദുർഗാ ക്ഷേത്രം",
            "temple_place": "കലൂർ",
            "temple_bill_title": "ശ്രീ ദുർഗാ ക്ഷേത്രം",
            "temple_bill_mid": "കൊച്ചി",
            "temple_bill_footer": "ഓം ദുർഗായै നമഃ"
        },
        {
            "temple_name": "ശ്രീ ശിവ ക്ഷേത്രം",
            "temple_place": "ആലപ്പാട്",
            "temple_bill_title": "ശ്രീ ശിവ ക്ഷേത്രം",
            "temple_bill_mid": "കോട്ടയം",
            "temple_bill_footer": "ഓം നമഃ ശിവായ"
        },
        {
            "temple_name": "ശ്രീ വിഘ്നേശ്വര ക്ഷേത്രം",
            "temple_place": "കോടുങ്ങല്ലൂർ",
            "temple_bill_title": "ശ്രീ വിഘ്നേശ്വര ക്ഷേത്രം",
            "temple_bill_mid": "വിനയാഗപുരം ",
            "temple_bill_footer": "ഓം വിഘ്നേശ്വരായ നമഃ"
        }
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
