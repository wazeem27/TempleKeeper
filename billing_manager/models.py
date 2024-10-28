from django.db import models
from django.conf import settings
from temple_inventory.models import InventoryItem
from temple_auth.models import Temple
from decimal import Decimal



class Bill(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="User")
    temple = models.ForeignKey(Temple, on_delete=models.CASCADE, verbose_name="Temple")
    items = models.ManyToManyField(InventoryItem, through='BillItem')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Total Amount")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def __str__(self):
        return f"Bill #{self.id} for {self.user.username} at {self.temple.temple_name}"

    class Meta:
        permissions = [
            ("can_add_bill", "Can add bill"),  # Change permission codename
            ("can_change_bill", "Can change bill"),
            ("can_delete_bill", "Can delete bill"),
            ("can_view_bill", "Can view bill"),
        ]

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.inventory_item.name} in Bill #{self.bill.id}"