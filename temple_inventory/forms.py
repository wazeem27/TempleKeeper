
from django import forms
from .models import InventoryItem


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'price', 'count', 'description']
        labels = {
            'name': 'Item Name',
            'price': 'Price per Item',
            'count': 'Available Count',
            'description': 'Description',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter a brief description'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        # Since temple will be set in the view, `temple` uniqueness check will be handled there.
        return name