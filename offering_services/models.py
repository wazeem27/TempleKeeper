from django.db import models
from django.conf import settings
from decimal import Decimal
from temple_auth.models import Temple


class VazhipaduOffering(models.Model):
    temple = models.ForeignKey(Temple, on_delete=models.CASCADE, related_name='vazhipadu_offerings')
    name = models.CharField(max_length=100, verbose_name='Offering Name')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price')
    description = models.TextField(blank=True, verbose_name='Description')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    def __str__(self):
        return f"{self.name} - ₹{self.price:.2f}"

    class Meta:
        verbose_name = 'Vazhipadu Offering'
        verbose_name_plural = 'Vazhipadu Offerings'
        ordering = ['order']
        permissions = [
            ("can_add_vazhipaduoffering", "Can add vazhipadu offering"),  # Change permission codename
            ("can_change_vazhipaduoffering", "Can change vazhipadu offering"),
            ("can_delete_vazhipaduoffering", "Can delete vazhipadu offering"),
            ("can_view_vazhipaduoffering", "Can view vazhipadu offering"),
        ]


class Star(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Star"
        verbose_name_plural = "Stars"