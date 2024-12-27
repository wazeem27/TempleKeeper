from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from temple_auth.models import UserProfile, Temple


class Command(BaseCommand):
    help = 'Create predefined sample users and assign them to groups, also creating UserProfile for each user.'

    sample_users = [
        {"username": "admin", "password": "Admin@123", "group": "Temple Admin"},
        {"username": "central_admin", "password": "Super_admin@123", "group": "Central Admin"},
        {"username": "biller_1", "password": "Biller_1@123", "group": "Billing Assistant"},
    ]

    def handle(self, *args, **kwargs):
        # Retrieve existing temples or create them if they don't exis
        # Get all existing temples to assign them later
        all_temples = Temple.objects.all()

        for user_data in self.sample_users:
            username = user_data["username"]
            password = user_data["password"]
            group_name = user_data["group"]

            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'User "{username}" created successfully.'))

                # Create UserProfile for the new user
                user_profile = UserProfile.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f'UserProfile created for "{username}".'))

                # Assign temples based on user group
                if group_name == "Central Admin":
                    # Assign all temples
                    user_profile.temples.set(all_temples)
                    self.stdout.write(self.style.SUCCESS(f'UserProfile for "{username}" linked to all temples.'))

                elif group_name == "Temple Admin":
                    # Assign the first two temples
                    user_profile.temples.set(all_temples)
                    self.stdout.write(self.style.SUCCESS(f'UserProfile for "{username}" linked to first two temples.'))

                elif group_name == "Billing Assistant":
                    # Assign the last temple only.,m,
                    user_profile.temples.set(all_temples)
                    self.stdout.write(self.style.SUCCESS(f'UserProfile for "{username}" linked to last temple only.'))

            else:
                self.stdout.write(self.style.WARNING(f'User "{username}" already exists.'))

            # Assign user to group
            group, group_created = Group.objects.get_or_create(name=group_name)
            if group_created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {group_name}'))
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f'User "{username}" added to group "{group_name}".'))

        self.stdout.write(self.style.SUCCESS('Finished creating users, assigning groups, and creating UserProfiles.'))
