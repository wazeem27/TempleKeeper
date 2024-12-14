from django import forms
from .models import VazhipaduOffering


class VazhipaduOfferingForm(forms.ModelForm):
    class Meta:
        model = VazhipaduOffering
        fields = ['name', 'price', 'allow_multiple']  # Include the new field
        labels = {
            'name': 'Offering Name',
            'price': 'Price',
            'allow_multiple': 'Allow Multiple',
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

    def clean_allow_multiple(self):
        allow_multiple = self.cleaned_data.get('allow_multiple')
        if not isinstance(allow_multiple, bool):
            raise forms.ValidationError("Invalid value for Allow Multiple.")
        return allow_multiple