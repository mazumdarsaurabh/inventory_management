
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import LoginForm, RegisterForm
from .models import InventoryItem
from django.shortcuts import render
from .forms import InventoryItemForm
from django.contrib.auth.decorators import login_required
from .forms import DeleteItemForm, StatusForm
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import get_object_or_404




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
def dashboard(request):
    items = InventoryItem.objects.all()
    return render(request, 'inventory/dashboard.html', {'items': items,'now': timezone.now()
                                                        })




@login_required
def add_item(request):
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added successfully!")
            return redirect('dashboard')
        else:
            print(form.errors) 
            return render(request, 'inventory/add_item.html', {'form': form, 'error': "Failed to add item. Please correct the form."})
          
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
from django.shortcuts import get_object_or_404

from django.shortcuts import render, redirect
from .forms import StatusForm  # or a custom UIDInputForm
from .models import InventoryItem

def modify_item(request):
    if request.method == 'POST':
        form = StatusForm(request.POST)  # using UID input form
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


# STATUS VIEW (No login required)
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