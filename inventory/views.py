from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from .forms import InventoryFilterForm

from .forms import (
    LoginForm,
    RegisterForm,
    InventoryItemForm,
    DeleteItemForm,
    StatusForm,
    InventoryFilterForm,
)
from .models import InventoryItem

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
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'inventory/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'inventory/register.html', {'form': form})


# ---------------- Dashboard ----------------

def dashboard(request):
    form = InventoryFilterForm(request.GET or None)
    items = InventoryItem.objects.all()
    if form.is_valid():
        item_name = form.cleaned_data.get('item_name')
        status = form.cleaned_data.get('status')
        location = form.cleaned_data.get('location')

        if item_name:
            items = items.filter(item_name=item_name)
        if status:
            items = items.filter(status=status)
        if location:
            items = items.filter(location=location)
    return render(request, 'inventory/dashboard.html', {'items': items, 'form': form})



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
            return render(request, 'inventory/add_item.html', {
                'form': form,
                'error': "Failed to add item. Please correct the form."
            })
    else:
        form = InventoryItemForm()

    return render(request, 'inventory/add_item.html', {'form': form})


@login_required
def delete_item(request):
    if request.method == 'POST':
        form = DeleteItemForm(request.POST)
        if form.is_valid():
            uid = form.cleaned_data['uid_no']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            try:
                item = InventoryItem.objects.get(uid_no=uid)
                if item.quantity >= quantity:
                    item.quantity -= quantity
                    if item.quantity == 0:
                        item.delete()
                        messages.success(request, f'Item with UID {uid} completely deleted.')
                    else:
                        item.save()
                        messages.success(request, f'{quantity} quantity removed from item UID {uid}.')
                else:
                    messages.error(request, 'Not enough quantity to delete.')
            except InventoryItem.DoesNotExist:
                messages.error(request, 'Item not found.')

            return redirect('dashboard')
    else:
        form = DeleteItemForm()
    return render(request, 'inventory/delete_item.html', {'form': form})


@login_required
def modify_item(request):
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            uid = form.cleaned_data['uid_no']
            try:
                item = InventoryItem.objects.get(uid_no=uid)
                return redirect('edit_item', uid=uid)
            except InventoryItem.DoesNotExist:
                form.add_error('uid_no', 'Item not found.')
    else:
        form = StatusForm()
    return render(request, 'inventory/modify_item.html', {'form': form})


@login_required
def edit_item(request, uid):
    item = get_object_or_404(InventoryItem, uid_no=uid)

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = InventoryItemForm(instance=item)

    return render(request, 'inventory/edit_item.html', {'form': form, 'uid': uid})


# ---------------- Status View ----------------

def status_item(request):
    item = None
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            uid_no = form.cleaned_data['uid_no']
            try:
                item = InventoryItem.objects.get(uid_no=uid_no)
            except InventoryItem.DoesNotExist:
                item = None
    else:
        form = StatusForm()
    return render(request, 'inventory/status_item.html', {'form': form, 'item': item})


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
            item.uid_no,
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
