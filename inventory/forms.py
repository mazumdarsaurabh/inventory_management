# inventory/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import InventoryItem, Location, Project
from django.contrib.auth.models import User
from django.utils import timezone

# ---------------------------
# User Authentication Forms
# ---------------------------

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

# ---------------------------
# Inventory Item Forms (Add/Edit)
# ---------------------------

class InventoryItemBaseForm(forms.ModelForm):
    item_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Laptop, Monitor'})
    )
    
    category = forms.ChoiceField(
        choices=InventoryItem.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select a category for automatic UID generation."
    )

    uid_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique ID (Auto-Generated)'})
    )
    serial_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number (Optional)'})
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        empty_label="Select Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=InventoryItem.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional detailed description'})
    )
    document = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'})
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        empty_label="Select Project (Optional)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )

    cpu = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Intel i7'})
    )
    gpu = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., NVIDIA RTX 3080'})
    )
    os = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Windows 10 Pro'})
    )
    installed_software = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List installed software, comma-separated'})
    )

    class Meta:
        model = InventoryItem
        fields = [
            'item_name', 'category', 'uid_no', 'serial_number', 'location', 'status',
            'description', 'document', 'image', 'project', 'quantity',
            'cpu', 'gpu', 'os', 'installed_software'
        ]


class AddItemForm(InventoryItemBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'uid_no' in self.fields:
            self.fields['uid_no'].widget = forms.HiddenInput()
            self.fields['uid_no'].required = False
        
        if 'quantity' in self.fields:
            self.fields['quantity'].initial = 1
            # Uncomment to hide quantity field if needed:
            # self.fields['quantity'].widget = forms.HiddenInput()


class EditItemForm(InventoryItemBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'uid_no' in self.fields:
            self.fields['uid_no'].widget.attrs['readonly'] = 'readonly'
            self.fields['uid_no'].required = False


# ---------------------------
# Delete Item Form
# ---------------------------

class DeleteItemForm(forms.Form):
    uid_no = forms.CharField(
        max_length=100, label="UID Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter UID to Delete'})
    )
    quantity = forms.IntegerField(
        min_value=1, initial=1, label="Quantity to Delete",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason_for_deletion = forms.CharField(
        max_length=255, label="Reason for Deletion",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )


# ---------------------------
# Status Check Form
# ---------------------------

class StatusCheckForm(forms.Form):
    uid_no = forms.CharField(
        max_length=100, label="UID No.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter UID'})
    )


# ---------------------------
# Modify Item Form
# ---------------------------

class ModifyItemForm(forms.Form):
    uid_no = forms.CharField(
        max_length=100, label="UID Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter UID'})
    )


# ---------------------------
# Inventory Filter Form
# ---------------------------

class InventoryFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by Name, UID, S/N etc.'
        })
    )
    item_name = forms.CharField(
        max_length=255, required=False, label="Item Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by Item Name'})
    )
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + list(InventoryItem.CATEGORY_CHOICES),
        required=False, label="Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(InventoryItem.STATUS_CHOICES),
        required=False, label="Status",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False, label="Location",
        empty_label="All Locations",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False, label="Project",
        empty_label="All Projects",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ---------------------------
# Inventory Transfer Form
# ---------------------------

class TransferForm(forms.Form):
    new_location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        empty_label="Select New Location",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_new_location_transfer'}),
        label="Transfer To Location"
    )

    new_project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        empty_label="Select Project (Optional)",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_project_transfer'}),
        label="New Project"
    )

    transfer_date = forms.DateField(
        label="Transfer Date",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.now().date(),
        required=False
    )
