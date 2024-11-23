from django import forms
from .models import VazhipaduOffering


class VazhipaduOfferingForm(forms.ModelForm):
    class Meta:
        model = VazhipaduOffering
        fields = ['name', 'price']  # Specify fields to include in the form
        labels = {
            'name': 'Offering Name',
            'price': 'Price',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Offering name is required.")
        return name

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Price must be a positive number.")
        return price