from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from temple_auth.models import UserProfile



class Command(BaseCommand):
    help = 'Create UserProfiles for all existing users without one.'

    def handle(self, *args, **kwargs):
        users_without_profile = User.objects.exclude(userprofile__isnull=False)

        for user in users_without_profile:
            UserProfile.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f'UserProfile created for "{user.username}".'))

        self.stdout.write(self.style.SUCCESS('Finished creating UserProfiles for all existing users.'))