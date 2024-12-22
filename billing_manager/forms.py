from django import forms


from .models import WalletCollection, Expense


class WalletCollectionForm(forms.ModelForm):
    class Meta:
        model = WalletCollection
        fields = [
            'coin_1', 'coin_2', 'coin_5', 
            'coin_10', 'coin_20', 'note_1', 'note_5', 
            'note_10', 'note_20', 'note_50', 'note_100',
            'note_200', 'note_500'
        ]
    coin_1 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 1 Rupee Coins', 'oninput': 'calculateTotal()'})
    )
    coin_2 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 2 Rupee Coins', 'oninput': 'calculateTotal()'})
    )
    coin_5 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 5 Rupee Coins', 'oninput': 'calculateTotal()'})
    )
    coin_10 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 10 Rupee Coins', 'oninput': 'calculateTotal()'})
    )
    coin_20 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 20 Rupee Coins', 'oninput': 'calculateTotal()'})
    )
    note_1 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 1 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_5 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 5 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_10 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 10 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_20 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 20 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_50 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 50 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_100 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 100 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_200 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 200 Rupee Notes', 'oninput': 'calculateTotal()'})
    )
    note_500 = forms.IntegerField(
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Count of 500 Rupee Notes', 'oninput': 'calculateTotal()'})
    )


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['item_name', 'price', 'quantity', 'expense_date']