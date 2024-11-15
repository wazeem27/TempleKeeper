from django.db import models
from django.conf import settings
from decimal import Decimal
from temple_auth.models import Temple

class InventoryItem(models.Model):
    temple = models.ForeignKey(Temple, on_delete=models.CASCADE, related_name='inventory_items')
    name = models.CharField(max_length=255, verbose_name="Item Name")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price per Item")
    count = models.PositiveIntegerField(default=0, verbose_name="Available Count")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        return f"{self.name} (Price: {self.price}, Count: {self.count})"

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ['name']
        permissions = [
            ("can_add_inventoryitem", "Can add inventory item"),  # Change permission codename
            ("can_change_inventoryitem", "Can change inventory item"),
            ("can_delete_inventoryitem", "Can delete inventory item"),
            ("can_view_inventoryitem", "Can view inventory item"),
        ]