from django.db import models
from django.conf import settings
from django.db.models import Max
from decimal import Decimal
from django.db import transaction
from temple_inventory.models import InventoryItem
from temple_auth.models import Temple
from django.core.exceptions import ValidationError
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
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Online', 'Online'),
    ]
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
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='Cash', verbose_name="Payment Method")
    online_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), blank=True, verbose_name="Online Amount")
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
    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.CharField(max_length=250, default="", blank=True)

    receipt_number = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Receipt Number", 
        editable=False
    )  # Unique per temple

    def __str__(self):
        return f"Bill #{self.receipt_number} for {self.user.username} at {self.temple.temple_name}"

    def is_split(self):
        """
        Returns whether the bill is split based on the presence of related bills.
        """
        return bool(self.related_bills)



    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.pk:  # If this is a new bill (creating a bill)
                # Get the last used receipt number for this temple and increment by 1
                last_receipt = (
                    Bill.objects.filter(temple=self.temple)
                    .select_for_update()
                    .aggregate(Max('receipt_number'))
                )['receipt_number__max']
                self.receipt_number = (last_receipt or 0) + 1  # Increment the last receipt number by 1
            else:
                # Prevent changing the receipt_number during an update
                original = Bill.objects.get(pk=self.pk)
                if original.receipt_number != self.receipt_number:
                    self.receipt_number = original.receipt_number  # Revert back to the original receipt_number

        super().save(*args, **kwargs)  # Call the super save method to actually save the object


    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_add_bill", "Can add bill"),
            ("can_change_bill", "Can change bill"),
            ("can_delete_bill", "Can delete bill"),
            ("can_view_bill", "Can view bill"),
        ]
        unique_together = ('temple', 'receipt_number')  # Ensures receipt numbers are unique per temple


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
