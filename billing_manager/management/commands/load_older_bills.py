import csv
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from billing_manager.models import Bill, BillOther, BillVazhipaduOffering, PersonDetail
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple, UserProfile
from django.db import transaction
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Load temple bill data from a CSV file into the database."

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help="Path to the CSV file")

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                with transaction.atomic():
                    for row in reader:
                        try:
                            self._process_row(row)
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error processing row: {row}. Error: {e}")
                            )

            self.stdout.write(self.style.SUCCESS(f"Successfully loaded data from {file_path}"))

        except FileNotFoundError:
            raise CommandError(f"File {file_path} does not exist.")
        except Exception as e:
            raise CommandError(f"An unexpected error occurred: {e}")

    def _process_row(self, row):
        """Processes a single row from the CSV file."""
        try:
            receipt_number = int(row['Receipt ID'])
            created_at = datetime.strptime(row['Created At'], "%a, %d %b %Y, %I:%M %p")
            created_by_username = row['Created By']
            pooja_name = row['Vazhipadu Name']
            person_name = row['Name']
            star_name = row['Star']
            price = Decimal(row['Amount'])

            # Fetch temple, user, and user profile
            temple = Temple.objects.first()  # Default temple logic, adjust as needed
            created_by = User.objects.get(username=created_by_username)
            user_profile = UserProfile.objects.get(user=created_by)

            # Handle split or consolidated bill logic
            if user_profile.is_split_bill:
                self._process_split_bill(
                    temple, created_by, created_at, receipt_number, pooja_name, 
                    person_name, star_name, price
                )
            else:
                self._process_single_bill(
                    temple, created_by, created_at, receipt_number, pooja_name, 
                    person_name, star_name, price
                )
        except User.DoesNotExist:
            raise CommandError(f"User with username '{row['Created By']}' does not exist.")
        except VazhipaduOffering.DoesNotExist:
            raise CommandError(f"Vazhipadu offering '{row['Vazhipadu Name']}' does not exist for the temple.")
        except Exception as e:
            raise CommandError(f"Error processing row: {row}. Error: {e}")

    def _process_split_bill(self, temple, created_by, created_at, receipt_number, pooja_name, person_name, star_name, price):
        """Handles the split bill logic."""
        bill = Bill.objects.create(
            receipt_number=receipt_number,
            user=created_by,
            temple=temple,
            total_amount=price,
            payment_method="cash",
        )

        # Override the created_at field
        bill._force_created_at = created_at
        bill.save()

        # Fetch vazhipadu offering
        vazhipadu_offering = VazhipaduOffering.objects.get(name=pooja_name, temple=temple)

        # Create BillVazhipaduOffering
        vazhipadu_bill = BillVazhipaduOffering.objects.create(
            bill=bill,
            vazhipadu_offering=vazhipadu_offering,
            quantity=1,
            price=price
        )

        # Create PersonDetail
        star = Star.objects.filter(name=star_name).first()
        PersonDetail.objects.create(
            bill_vazhipadu_offering=vazhipadu_bill,
            person_name=person_name,
            person_star=star
        )

    def _process_single_bill(self, temple, created_by, created_at, receipt_number, pooja_name, person_name, star_name, price):
        """Handles the single consolidated bill logic."""
        bill = Bill.objects.create(
            receipt_number=receipt_number,
            user=created_by,
            temple=temple,
            total_amount=price,
            payment_method="cash",
        )

        # Override the created_at field
        bill._force_created_at = created_at
        bill.save()

        # Fetch vazhipadu offering
        vazhipadu_offering = VazhipaduOffering.objects.get(name=pooja_name, temple=temple)

        # Create BillVazhipaduOffering
        vazhipadu_bill = BillVazhipaduOffering.objects.create(
            bill=bill,
            vazhipadu_offering=vazhipadu_offering,
            quantity=1,
            price=price
        )

        # Create PersonDetail
        star = Star.objects.filter(name=star_name).first()
        PersonDetail.objects.create(
            bill_vazhipadu_offering=vazhipadu_bill,
            person_name=person_name,
            person_star=star
        )
