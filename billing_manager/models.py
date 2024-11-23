from django.db import models
from django.conf import settings
from decimal import Decimal
from temple_inventory.models import InventoryItem
from temple_auth.models import Temple
from offering_services.models import VazhipaduOffering, Star



class BillOther(models.Model):
    # Use the string reference to avoid circular import
    bill = models.ForeignKey(
        'Bill',  # Referencing Bill as a string
        on_delete=models.CASCADE,
        related_name='bill_other_items',  # Access related BillOther items using `bill_other_items`
        verbose_name="Bill"
    )
    person_star = models.ForeignKey(
        Star, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name="Person Star"
    )
    person_name = models.CharField(max_length=255, verbose_name="Person Name")
    vazhipadu = models.CharField(max_length=255, verbose_name="Vazhipadu")
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.person_name} x {self.vazhipadu} in Bill #{self.bill.id}"


class Bill(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="User"
    )
    temple = models.ForeignKey(
        Temple, 
        on_delete=models.CASCADE, 
        verbose_name="Temple"
    )
    # Removed ManyToManyField, now accessed via BillOther's ForeignKey to Bill
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="Total Amount"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Created At"
    )
    related_bills = models.TextField(
        blank=True, 
        verbose_name="Related Bills (CSV)"
    )  # Updated to TextField for longer entries
    is_printed = models.BooleanField(
        default=False, 
        verbose_name="Is Printed"
    )

    def __str__(self):
        return f"Bill #{self.id} for {self.user.username} at {self.temple.temple_name}"

    def is_split(self):
        """
        Returns whether the bill is split based on the presence of related bills.
        """
        return bool(self.related_bills)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_add_bill", "Can add bill"),
            ("can_change_bill", "Can change bill"),
            ("can_delete_bill", "Can delete bill"),
            ("can_view_bill", "Can view bill"),
        ]


class BillVazhipaduOffering(models.Model):
    bill = models.ForeignKey(
        'Bill',  # Referencing Bill as a string
        on_delete=models.CASCADE, 
        related_name='bill_vazhipadu_offerings',
        verbose_name="Bill"
    )
    vazhipadu_offering = models.ForeignKey(
        VazhipaduOffering, 
        on_delete=models.CASCADE, 
        verbose_name="Vazhipadu Offering"
    )
    person_name = models.CharField(
        max_length=255, 
        verbose_name="Person Name"
    )
    person_star = models.ForeignKey(
        Star, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name="Person Star"
    )
    quantity = models.PositiveIntegerField(
        default=1, 
        verbose_name="Quantity"
    )  # Default quantity is 1
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Price"
    )

    def __str__(self):
        return f"{self.quantity} x {self.vazhipadu_offering.name} in Bill #{self.bill.id}"
