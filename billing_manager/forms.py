from django import forms


from .models import WalletCollection


class WalletCollectionForm(forms.ModelForm):
    class Meta:
        model = WalletCollection
        fields = [
            'counter_cash', 'coin_1_rupee', 'coin_2_rupees', 'coin_5_rupees', 
            'coin_10_rupees', 'coin_20_rupees', 'note_1_rupees', 'note_5_rupees', 
            'note_10_rupees', 'note_20_rupees', 'note_50_rupees', 'note_100_rupees',
            'note_200_rupees', 'note_500_rupees'
        ]

    counter_cash = forms.DecimalField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Counter Cash'})
    )
    coin_1_rupee = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 1 Rupee Coins'})
    )
    coin_2_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 2 Rupee Coins'})
    )
    coin_5_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 5 Rupee Coins'})
    )
    coin_10_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 10 Rupee Coins'})
    )
    coin_20_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 20 Rupee Coins'})
    )
    note_1_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 1 Rupee Notes'})
    )
    note_5_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 5 Rupee Notes'})
    )
    note_10_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 10 Rupee Notes'})
    )
    note_20_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 20 Rupee Notes'})
    )
    note_50_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 50 Rupee Notes'})
    )
    note_100_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 100 Rupee Notes'})
    )
    note_200_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 200 Rupee Notes'})
    )
    note_500_rupees = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 500 Rupee Notes'})
    )