from django import forms


class WalletAdjustmentForm(forms.Form):
    amount_tzs = forms.IntegerField(label="Amount (TZS)")
    note = forms.CharField(
        label="Reason",
        min_length=10,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_amount_tzs(self):
        amount = self.cleaned_data["amount_tzs"]
        if amount == 0:
            raise forms.ValidationError("Amount must not be zero.")
        return amount
