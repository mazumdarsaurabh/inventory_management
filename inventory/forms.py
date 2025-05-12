from django import forms
from .models import InventoryItem
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# Form to add a new inventory item
class InventoryFilterForm(forms.Form):
    category = forms.ChoiceField(required=False)
    status = forms.ChoiceField(required=False)
    location = forms.ChoiceField(required=False)


    def __init__(self, *args, **kwargs):
        super(InventoryFilterForm, self).__init__(*args, **kwargs)


# Form to delete an inventory item
class DeleteItemForm(forms.Form):
    uid_no = forms.CharField(label='UID Number', max_length=50)
    quantity = forms.IntegerField(min_value=1, label="Quantity to Delete")
    reason = forms.CharField(widget=forms.Textarea, required=True)

# Form to check the status of an item
class StatusForm(forms.Form):
    uid_no = forms.CharField(label='UID Number', max_length=50)

# User Registration Form
class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

# User Login Form
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class InventoryFilterForm(forms.Form):
    category = forms.ChoiceField(required=False)
    status = forms.ChoiceField(required=False)
    location = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', 'All Categories')] + list(
            InventoryItem.objects.values_list('category', 'category').distinct()
        )
        self.fields['status'].choices = [('', 'All Status')] + list(
            InventoryItem.objects.values_list('status', 'status').distinct()
        )
        self.fields['location'].choices = [('', 'All Locations')] + list(
            InventoryItem.objects.values_list('location', 'location').distinct()
        )
    class InventoryForm(forms.ModelForm):
      class Meta:
        model = InventoryItem
        fields = '__all__'
class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = '__all__'
