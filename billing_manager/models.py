from django.db import models
from django.conf import settings
from django.db.models import Max
from decimal import Decimal
import uuid
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
    # New UUID field
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False, 
        verbose_name="Unique ID"
    )
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
            if self._state.adding:  # Detect if this is a new instance
                # Get the last used receipt number for this temple and increment by 1
                last_receipt = (
                    Bill.objects.filter(temple=self.temple)
                    .select_for_update()
                    .aggregate(Max('receipt_number'))
                )['receipt_number__max']
                self.receipt_number = (last_receipt or 0) + 1  # Increment the last receipt number by 1
            else:
                # For existing instances, ensure receipt_number is not modified
                original = Bill.objects.filter(pk=self.pk).first()
                if not original:
                    raise ValueError("Attempted to update a Bill that does not exist.")
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
        unique_together = ('temple', 'receipt_number')  # Receipt numbers unique per temple



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
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantity"
    )  # Default quantity is 1
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Price"
    )  # Can be calculated dynamically based on quantity

    def __str__(self):
        return f"{self.quantity} x {self.vazhipadu_offering.name} in Bill #{self.bill.id}"


class PersonDetail(models.Model):
    bill_vazhipadu_offering = models.ForeignKey(
        BillVazhipaduOffering,
        on_delete=models.CASCADE,
        related_name='person_details',
        verbose_name="Bill Vazhipadu Offering"
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

    def __str__(self):
        return f"{self.person_name} ({self.person_star})"



class WalletCollection(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False, 
        verbose_name="Unique ID"
    )
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
    date = models.DateField()
        
    # Fields for coins (1, 2, 5, 10 rupees)
    coin_1 = models.IntegerField(default=0)
    coin_2 = models.IntegerField(default=0)
    coin_5 = models.IntegerField(default=0)
    coin_10 = models.IntegerField(default=0)
    coin_20 = models.IntegerField(default=0)
    
    # Fields for notes (5, 10, 20 rupees)
    note_1 = models.IntegerField(default=0)
    note_5 = models.IntegerField(default=0)
    note_10 = models.IntegerField(default=0)
    note_20 = models.IntegerField(default=0)
    note_50 = models.IntegerField(default=0)
    note_100 = models.IntegerField(default=0)
    note_200 = models.IntegerField(default=0)
    note_500 = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet Collection for {self.date}"

    def __sum__(self):
        # Calculate the sum for coins (multiplying denomination by count)
        coin_total = (self.coin_1 * 1) + (self.coin_2 * 2) + (self.coin_5 * 5) + (self.coin_10 * 10) + (self.coin_20 * 20)
        
        # Calculate the sum for notes (multiplying denomination by count)
        note_total = (self.note_1 * 1) + (self.note_5 * 5) + (self.note_10 * 10) + (self.note_20 * 20) + (self.note_50 * 50) + \
                     (self.note_100 * 100) + (self.note_200 * 200) + (self.note_500 * 500)
        
        # Return the total sum of coins and notes
        return coin_total + note_total



class Expense(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False, 
        verbose_name="Unique ID"
    )
    temple = models.ForeignKey(Temple, on_delete=models.CASCADE, related_name='temple_expenses')
    item_name = models.CharField(max_length=255, verbose_name="Item Name")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    quantity = models.TextField(default=1, blank=True, verbose_name="Quantity")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="User"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    expense_date = models.DateTimeField()

    @property
    def total_cost(self):
        """Calculate the total cost for the item."""
        return self.price * self.quantity

    def __str__(self):
        return f"{self.item_name} - {self.quantity} x {self.price}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"