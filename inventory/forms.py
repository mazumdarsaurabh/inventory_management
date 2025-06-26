# forms.py
from django import forms
from .models import InventoryItem
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# Inventory Filter Form (multi-column dropdown)
class InventoryFilterForm(forms.Form):
    item_name = forms.ChoiceField(required=False)
    status = forms.ChoiceField(required=False)
    location = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_name'].choices = [('', 'All')] + list(
            InventoryItem.objects.values_list('item_name', 'item_name').distinct()
        )
        self.fields['status'].choices = [('', 'All')] + list(
            InventoryItem.objects.values_list('status', 'status').distinct()
        )
        self.fields['location'].choices = [('', 'All')] + list(
            InventoryItem.objects.values_list('location', 'location').distinct()
        )

# Other forms

class DeleteItemForm(forms.Form):
    uid_no = forms.CharField(label='UID Number', max_length=50)
    quantity = forms.IntegerField(min_value=1, label="Quantity to Delete")
    reason = forms.CharField(widget=forms.Textarea, required=True)

class StatusForm(forms.Form):
    uid_no = forms.CharField(label='UID Number', max_length=50)

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = '__all__'
