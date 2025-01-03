from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser


class Temple(models.Model):
    temple_name = models.CharField(max_length=500)
    temple_place = models.CharField(max_length=120, blank=True, null=True)  # Optional field
    temple_short_name = models.CharField(max_length=120, blank=True, null=True)  # Optional field
    temple_bill_title = models.CharField(max_length=300, blank=True, null=True)
    temple_bill_mid = models.CharField(max_length=400, blank=True, null=True)
    temple_bill_footer = models.CharField(max_length=320, blank=True, null=True)
    deactivate = models.BooleanField(default=False)  # For deactivating temple

    class Meta:
        unique_together = ['temple_name', 'temple_place']  # Ensures unique combination of name and location
        verbose_name = 'Temple'
        verbose_name_plural = 'Temples'

    def __str__(self):
        return f"{self.temple_name} - {self.temple_place}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the original save method

        # After saving the temple, link it to all existing Central Admin users
        self.assign_temple_to_central_admins()

    def assign_temple_to_central_admins(self):
        # Get all Central Admin users and link them to the newly created temple
        central_admins = User.objects.filter(groups__name="Central Admin")
        for central_admin in central_admins:
            user_profile, created = UserProfile.objects.get_or_create(user=central_admin)
            user_profile.temples.add(self)  # Add the current temple instance to the user's profile


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    temples = models.ManyToManyField(Temple, blank=True)  # Multiple temples for each user
    is_approved_by_admin = models.BooleanField(default=False)  # For admin approval
    is_staff = models.BooleanField(default=False)  # To differentiate between admin and counter users
    is_split_bill = models.BooleanField(default=False)  # To differentiate between admin and counter users

    def __str__(self):
        return self.user.username

    def has_selected_temple(self):
        # Helper method to check if the user has selected a temple
        return hasattr(self, 'selected_temple') and self.selected_temple is not None



class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note by {self.user.username} at {self.created_at}"