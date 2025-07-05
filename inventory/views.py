from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse

# Make sure you have these forms imported correctly
from .forms import (
    LoginForm,
    RegisterForm,
    InventoryItemForm,
    DeleteItemForm,
    StatusForm,  # Used for modify_item and status_item search
    InventoryFilterForm,
)
from .models import InventoryItem  # Make sure your InventoryItem model is imported

import openpyxl


# ---------------- User Auth ----------------

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, 'Logged in successfully!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'inventory/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
    else:
        form = RegisterForm()
    return render(request, 'inventory/register.html', {'form': form})


# ---------------- Dashboard ----------------

@login_required
def dashboard(request):
    filter_form = InventoryFilterForm(request.GET or None)
    inventory_items = InventoryItem.objects.all()

    if filter_form.is_valid():
        item_name_query = filter_form.cleaned_data.get('item_name')
        status_query = filter_form.cleaned_data.get('status')
        location_query = filter_form.cleaned_data.get('location')

        if item_name_query:
            inventory_items = inventory_items.filter(item_name__icontains=item_name_query)
        if status_query:
            inventory_items = inventory_items.filter(status=status_query)
        if location_query:
            inventory_items = inventory_items.filter(location=location_query)

    return render(request, 'inventory/dashboard.html', {
        'items': inventory_items,
        'filter_form': filter_form
    })

# ---------------- Inventory Management ----------------

@login_required
def add_item(request):
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to add item. Please correct the form errors.")
            return render(request, 'inventory/add_item.html', {'form': form})
    else:
        form = InventoryItemForm()
    return render(request, 'inventory/add_item.html', {'form': form})

# This function handles deletion of a specific item by its primary key (from dashboard table rows)
@login_required
def delete_item(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == 'POST':
        # You might want a more elaborate confirmation page/logic
        item.delete()
        messages.success(request, f'Item "{item.item_name}" (UID: {item.uid_number}) completely deleted.')
        return redirect('dashboard')
    
    # Render a confirmation page for GET requests to confirm deletion
    return render(request, 'inventory/delete_item_confirm.html', {'item': item})

# This function handles general deletion (search by UID/quantity from a form)
@login_required
def delete_item_general(request): # <-- THIS FUNCTION IS NOW INCLUDED
    if request.method == 'POST':
        form = DeleteItemForm(request.POST)
        if form.is_valid():
            uid = form.cleaned_data['uid_no']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            try:
                item = InventoryItem.objects.get(uid_no=uid) # Use your model's correct UID field name
                if item.quantity >= quantity:
                    item.quantity -= quantity
                    if item.quantity == 0:
                        item.delete()
                        messages.success(request, f'Item with UID {uid} completely deleted due to: {reason}.')
                    else:
                        item.save()
                        messages.success(request, f'{quantity} quantity removed from item UID {uid}. Reason: {reason}.')
                else:
                    messages.error(request, 'Not enough quantity to delete.')
            except InventoryItem.DoesNotExist:
                messages.error(request, 'Item not found.')
            return redirect('dashboard')
    else:
        form = DeleteItemForm()
    return render(request, 'inventory/delete_item_general.html', {'form': form})


# This is the 'modify' function that accepts a UID search (for the top button)
@login_required
def modify_item(request): # <-- THIS FUNCTION IS NOW INCLUDED
    if request.method == 'POST':
        form = StatusForm(request.POST) # Using StatusForm, ensure it has 'uid_no'
        if form.is_valid():
            uid = form.cleaned_data['uid_no']
            try:
                item = InventoryItem.objects.get(uid_no=uid) # Use your model's UID field name (e.g., uid_number)
                messages.info(request, f'Found item "{item.item_name}". Redirecting to edit page.')
                return redirect('edit_item', pk=item.pk) # Redirect to edit_item with the actual PK
            except InventoryItem.DoesNotExist:
                messages.error(request, f'Item with UID "{uid}" not found.')
                form.add_error('uid_no', 'Item not found.') # Add error to the form field
    else:
        form = StatusForm() # Initialize empty form for GET request
    return render(request, 'inventory/modify_item.html', {'form': form}) # You'll need this template


# This view is for editing a specific item by its primary key (from dashboard table rows or modify_item)
@login_required
def edit_item(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Item "{item.item_name}" updated successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to update item. Please correct the form errors.")
    else:
        form = InventoryItemForm(instance=item)

    return render(request, 'inventory/edit_item.html', {'form': form, 'item': item})

# This function handles checking status of a specific item by its primary key (from dashboard table rows)
@login_required
def status_item(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    return render(request, 'inventory/status_item.html', {'item': item})

# This function handles general status check (search by UID from a form)
@login_required
def status_item_general(request): # <-- THIS FUNCTION IS NOW INCLUDED
    item = None # Initialize item to None
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            uid_no = form.cleaned_data['uid_no']
            try:
                item = InventoryItem.objects.get(uid_no=uid_no) # Use your model's correct UID field name
            except InventoryItem.DoesNotExist:
                messages.error(request, f'Item with UID "{uid_no}" not found.')
                item = None # Ensure item is None if not found
    else:
        form = StatusForm()
    return render(request, 'inventory/status_item_general.html', {'form': form, 'item': item})


# ---------------- Export to Excel ----------------
@login_required
def export_inventory_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory Data"

    headers = [
        'Item Name', 'UID No', 'Serial Number',
        'Quantity', 'Location', 'Status', 'Description'
    ]
    ws.append(headers)

    for item in InventoryItem.objects.all():
        ws.append([
            item.item_name,
            item.uid_no, # Assumed uid_number, ensure it matches your model field
            item.serial_number,
            item.quantity,
            item.location,
            item.status,
            item.description or "",
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventory_data.xlsx'
    wb.save(response)
    return response