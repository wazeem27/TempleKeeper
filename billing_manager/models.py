from django.db import models
from django.conf import settings
from decimal import Decimal
from temple_inventory.models import InventoryItem
from temple_auth.models import Temple
from offering_services.models import VazhipaduOffering, Star


class Bill(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="User")
    temple = models.ForeignKey(Temple, on_delete=models.CASCADE, verbose_name="Temple")
    inventory_items = models.ManyToManyField(InventoryItem, through='BillInventoryItem')
    vazhipadu_offerings = models.ManyToManyField(VazhipaduOffering, through='BillVazhipaduOffering')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Total Amount")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def __str__(self):
        return f"Bill #{self.id} for {self.user.username} at {self.temple.temple_name}"

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_add_bill", "Can add bill"),
            ("can_change_bill", "Can change bill"),
            ("can_delete_bill", "Can delete bill"),
            ("can_view_bill", "Can view bill"),
        ]


class BillInventoryItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_inventory_items')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.inventory_item.name} in Bill #{self.bill.id}"


class BillVazhipaduOffering(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_vazhipadu_offerings')
    vazhipadu_offering = models.ForeignKey(VazhipaduOffering, on_delete=models.CASCADE)
    person_name = models.CharField(max_length=255, verbose_name="Person Name")
    person_star = models.ForeignKey(Star, on_delete=models.CASCADE, blank=True, null=True)  # Optional field
    quantity = models.PositiveIntegerField(default=1)  # Default quantity for offerings
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.vazhipadu_offering.name} in Bill #{self.bill.id}"
