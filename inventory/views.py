# inventory_management/inventory/views.py

import json
import re
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Count, Q, F
from django.db import models
from django.views.decorators.http import require_POST
from .models import InventoryItem

# Pagination imports
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# Ensure all necessary forms are imported
from .forms import (
    LoginForm,
    RegisterForm,
    AddItemForm,
    EditItemForm,
    DeleteItemForm,
    StatusCheckForm,
    ModifyItemForm,
    InventoryFilterForm,
    TransferForm
)

# Import all models needed
from .models import InventoryItem, Location, Project, InventoryLog, UIDCategorySequence
# Assuming Category is NOT a separate model, otherwise you'd import it here too.
from django.contrib.auth.models import User

# For Excel export
import openpyxl
from openpyxl.styles import Font
from openpyxl import Workbook
import mimetypes

import logging
logger = logging.getLogger(__name__)


# --- Helper function to create log entries ---
def create_log_entry(user, item_obj, action, details=None, uid_number_for_log=None):
    """
    Creates a new log entry in the InventoryLog model.
    :param user: The User object performing the action. Can be None for actions like logout if model allows.
    :param item_obj: The InventoryItem object related to the log. Can be None if item is deleted.
    :param action: The type of action (e.g., 'added', 'deleted', 'updated').
    :param details: Additional details for the log entry.
    :param uid_number_for_log: Explicit UID to store in log, especially if item_obj is None.
    """
    log_uid = uid_number_for_log
    if item_obj and item_obj.uid_no:
        log_uid = item_obj.uid_no

    # Fallback if no UID is explicitly provided and item_obj is None, try to extract from details
    if not log_uid and action == 'deleted' and details:
        match = re.search(r'\(UID: ([\w-]+)\)', details) # More robust regex for UID (allowing hyphen)
        if match:
            log_uid = match.group(1)

    # Ensure the 'user' field in InventoryLog is correctly set if you named it 'user' and not 'acted_by'.
    # Based on your provided code, it's 'acted_by' (though your log function parameter is 'user').
    # Let's assume your InventoryLog model has 'user' as the ForeignKey to User.
    InventoryLog.objects.create(
        user=user if user and user.is_authenticated else None,
        item=item_obj, # This can now be None due to models.SET_NULL (assuming your model is configured this way)
        uid_no=log_uid, # Store the UID directly in the log for historical purposes
        action=action,
        details=details
    )

# ---------------- User Auth ----------------

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                create_log_entry(user, None, 'login', f"User '{username}' logged in.")
                messages.success(request, f"Welcome back, {username}!")
                return redirect('inventory:dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = LoginForm()
    return render(request, 'inventory/login.html', {'form': form})

@login_required
def user_logout(request):
    username = request.user.username
    logout(request)
    create_log_entry(None, None, 'logout', f"User '{username}' logged out.")
    messages.success(request, "You have been logged out.")
    return redirect('inventory:login')

def user_register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            create_log_entry(user, None, 'registered', f"New user '{user.username}' registered.")
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('inventory:dashboard')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = RegisterForm()
    return render(request, 'inventory/register.html', {'form': form})


# ---------------- Dashboard & Filtering ----------------

@login_required
def dashboard_view(request):
    # CORRECTED: Removed 'category' from select_related here.
    # It seems your InventoryItem.category is a CharField, not a ForeignKey.
    items = InventoryItem.objects.all().order_by('item_name').select_related('location', 'project')
    filter_form = InventoryFilterForm(request.GET)

    search_query = ''
    if filter_form.is_valid():
        search_query = filter_form.cleaned_data.get('search', '')
        if search_query:
            items = items.filter(
                Q(item_name__icontains=search_query) |
                Q(uid_no__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(location__name__icontains=search_query) |
                Q(project__name__icontains=search_query) |
                # CORRECTED: If category is a CharField, you cannot use __name or __prefix
                # You must access it directly like this:
                Q(category__icontains=search_query) |
                # If you have a 'prefix' field directly on InventoryItem and it's also a CharField:
                # Q(prefix__icontains=search_query) |
                # If 'prefix' was meant to be a field on a *related* Category model, and category is a CharField,
                # then this line (Q(category__prefix__icontains=search_query)) is also incorrect.
                # Assuming `category` is a single CharField for the item's category:
                # (You will need to ensure your InventoryItem model does not have a `prefix` field
                # or adjust this line based on its actual type).
                # For now, I'm commenting out the problematic `category__prefix` and adjusting `category__name`.
                # If your Category model existed and had a prefix, the original was correct, but then
                # InventoryItem.category *would* be a ForeignKey, which the error disproves.
                # So, I'm assuming 'category' is a CharField and 'prefix' logic needs to be re-evaluated.
                # If 'prefix' is a separate field on InventoryItem, then add: Q(prefix__icontains=search_query)
                # If there's no 'prefix' field at all, remove this Q entirely.
                # For safety, removing `category__prefix` and just using `category__icontains`.
                # If `UIDCategorySequence` is used for category prefixes for UID generation,
                # this Q clause might not be for searching `InventoryItem.category` but rather for related UID logic.
                # However, the error refers to `InventoryItem.category`.
                Q(cpu__icontains=search_query) |
                Q(gpu__icontains=search_query) |
                Q(os__icontains=search_query) |
                Q(installed_software__icontains=search_query) |
                Q(status__icontains=search_query)
            ).distinct()

    paginator = Paginator(items, 10)
    page = request.GET.get('page')
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    context = {
        'items': items_page,
        'filter_form': filter_form,
        'search_query': search_query,
        'current_time': timezone.now(),
        'user': request.user,
        'transfer_form': TransferForm(),
        'locations': Location.objects.all(),
        'projects': Project.objects.all(),
    }
    return render(request, 'inventory/dashboard.html', context)

# ---------------- Inventory Management with Logging ----------------

@login_required
def add_item(request):
    if request.method == 'POST':
        form = AddItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.added_by = request.user
            item.save()
            create_log_entry(request.user, item, 'added',
                             f"New item '{item.item_name}' (UID: {item.uid_no}) with quantity {item.quantity} added.",
                             uid_number_for_log=item.uid_no)
            messages.success(request, f"Item '{item.item_name}' (UID: {item.uid_no}) added successfully!")
            return redirect('inventory:dashboard')
        else:
            messages.error(request, "Failed to add item. Please correct the errors.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = AddItemForm()
    return render(request, 'inventory/add_item.html', {'form': form})

@login_required
@transaction.atomic
def delete_item_general(request):
    if request.method == 'POST':
        form = DeleteItemForm(request.POST)
        if form.is_valid():
            uid = form.cleaned_data['uid_no']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason_for_deletion']

            try:
                item = get_object_or_404(InventoryItem, uid_no=uid)
                item_name = item.item_name
                item_uid = item.uid_no
                current_quantity = item.quantity

                if quantity > current_quantity:
                    messages.error(request, f"Cannot delete {quantity} of item {uid}. Only {current_quantity} available.")
                    return render(request, 'inventory/delete_item_general.html', {'form': form})

                log_details = ""
                if quantity == current_quantity:
                    log_details = (f"Item '{item_name}' (UID: {item_uid}) fully deleted. "
                                   f"Original Quantity: {current_quantity}. Reason: {reason or 'No reason provided'}.")
                    create_log_entry(request.user, None, 'deleted', log_details, uid_number_for_log=item_uid)
                    item.delete()
                    messages.success(request, f'Item with UID {uid} fully deleted. {log_details}')
                else:
                    item.quantity -= quantity
                    item.save()
                    log_details = (f"Reduced quantity of '{item_name}' (UID: {item_uid}) by {quantity}. "
                                   f"New quantity: {item.quantity}. Reason: {reason or 'No reason provided'}.")
                    create_log_entry(request.user, item, 'quantity_reduced', log_details, uid_number_for_log=item_uid)
                    messages.success(f'Quantity of item with UID {uid} reduced. {log_details}')

                return redirect('inventory:dashboard')

            except InventoryItem.DoesNotExist:
                messages.error(request, f'Item with UID "{uid}" not found.')
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
                logger.exception(f"Error during general item deletion for UID: {uid}")

            return render(request, 'inventory/delete_item_general.html', {'form': form})
        else:
            messages.error(request, 'Please correct the errors.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            return render(request, 'inventory/delete_item_general.html', {'form': form})
    else:
        form = DeleteItemForm()
    return render(request, 'inventory/delete_item_general.html', {'form': form})

@login_required
@transaction.atomic
def delete_item_by_pk(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        item_name = item.item_name
        item_uid = item.uid_no
        item_quantity = item.quantity

        log_details = f"Item '{item_name}' (UID: {item_uid}, Quantity: {item_quantity}) deleted directly by PK."
        create_log_entry(request.user, None, 'deleted', log_details, uid_number_for_log=item_uid)

        item.delete()
        messages.success(request, f'Item "{item_name}" (UID: {item_uid}) deleted successfully.')
        return redirect('inventory:dashboard')
    return render(request, 'inventory/delete_item_confirm.html', {'item': item})

@login_required
def modify_item(request):
    if request.method == 'POST':
        search_form = ModifyItemForm(request.POST)
        if search_form.is_valid():
            uid = search_form.cleaned_data['uid_no']
            try:
                item = InventoryItem.objects.get(uid_no=uid)
                messages.info(request, f'Found item "{item.item_name}". You can now modify its details.')
                return redirect('inventory:edit_item', pk=item.pk)
            except InventoryItem.DoesNotExist:
                messages.error(request, f'Item with UID "{uid}" not found for modification.')
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while searching: {e}")
                logger.exception(f"Error during modify item search for UID: {uid}")
        else:
            messages.error(request, 'Please correct the errors in the UID search.')
            for field, errors in search_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

    search_form = ModifyItemForm()
    context = {
        'search_form': search_form,
    }
    return render(request, 'inventory/modify_item.html', context)

@login_required
def edit_item(request, pk):
    # Removed 'category' from select_related here, as it's not a ForeignKey
    item = get_object_or_404(InventoryItem.objects.select_related('location', 'project'), pk=pk)

    if request.method == 'POST':
        original_values = {
            'item_name': item.item_name,
            # 'category': item.category, # Keep commented unless it's a ForeignKey
            'uid_no': item.uid_no,
            'serial_number': item.serial_number,
            'location': item.location,
            'status': item.status,
            'description': item.description,
            'project': item.project,
            'quantity': item.quantity,
            'document': item.document.name if item.document else None,
            'image': item.image.name if item.image else None,
            'cpu': item.cpu,
            'gpu': item.gpu,
            'os': item.os,
            'installed_software': item.installed_software,
        }

        form = EditItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            updated_item = form.save(commit=False)

            changes = []
            for field_name in form.changed_data:
                try:
                    model_field = InventoryItem._meta.get_field(field_name)
                except models.FieldDoesNotExist:
                    logger.warning(f"Field '{field_name}' not found in InventoryItem model fields.")
                    continue

                original_value = original_values.get(field_name)
                current_value = getattr(updated_item, field_name)

                display_original = original_value
                display_current = current_value

                if isinstance(model_field, models.ForeignKey):
                    display_original = original_value.name if original_value else 'None'
                    display_current = current_value.name if current_value else 'None'
                elif isinstance(model_field, (models.FileField, models.ImageField)):
                    new_file_uploaded = field_name in request.FILES
                    file_cleared = form.cleaned_data.get(f'clear_{field_name}')

                    if new_file_uploaded:
                        display_original = "existing file" if original_value else "no file"
                        display_current = f"new file: {request.FILES[field_name].name}"
                    elif file_cleared and original_value:
                        display_original = original_value
                        display_current = "file cleared"
                    else:
                        continue

                if str(display_original) == str(display_current):
                    continue

                display_original_str = str(display_original) if display_original is not None and display_original != '' else 'Empty'
                display_current_str = str(current_value) if current_value is not None and current_value != '' else 'Empty'

                changes.append(f"{model_field.verbose_name}: '{display_original_str}' to '{display_current_str}'")

            updated_item.save()

            if changes:
                log_details = f"Updated item '{updated_item.item_name}' (UID: {updated_item.uid_no}). Changes: {'; '.join(changes)}"
                create_log_entry(request.user, updated_item, 'updated', log_details, uid_number_for_log=updated_item.uid_no)
                messages.success(request, f'Item "{updated_item.item_name}" (UID: {updated_item.uid_no}) updated successfully! Changes: {", ".join(changes)}')
            else:
                messages.info(request, 'No changes detected for the item.')
            return redirect('inventory:item_details', pk=item.pk)
        else:
            messages.error(request, "Failed to update item. Please correct the errors.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = EditItemForm(instance=item)

    context = {
        'form': form,
        'item': item,
    }
    return render(request, 'inventory/edit_item.html', context)


@login_required
@login_required
def status_check(request):
    print("--- status_check view entered ---") # Debug print
    print(f"Request method: {request.method}") # Debug print

    item_status_data = None
    form = StatusCheckForm() # Initialize an empty form for initial GET request

    if request.method == 'GET':
        print(f"Request GET data: {request.GET}") # CRITICAL DEBUG PRINT

        form = StatusCheckForm(request.GET)
        if form.is_valid():
            uid_no = form.cleaned_data['uid_no']
            print(f"Form is valid. UID No: {uid_no}") # Debug print

            try:
                # CHANGE THIS LINE: Use InventoryItem instead of Item
                item_status_data = InventoryItem.objects.get(uid_no=uid_no)
                print(f"Item found: {item_status_data.item_name}") # Debug print
                messages.success(request, f"Status found for UID: {uid_no}")
            except InventoryItem.DoesNotExist: # Also change this exception
                item_status_data = None
                print(f"Item with UID {uid_no} not found.") # Debug print
                messages.error(request, f"No item found with UID: {uid_no}")
            except Exception as e:
                item_status_data = None
                print(f"An error occurred while fetching item: {e}") # Debug print
                messages.error(request, f"An error occurred: {e}")
        else:
            print(f"Form is NOT valid. Errors: {form.errors}") # Debug print
            # Django will automatically include form.errors in the context if you pass the form
            messages.error(request, "Please correct the errors below.")

    context = {
        'form': form,
        'item_status_data': item_status_data,
    }
    print("--- Exiting status_check view ---") # Debug print
    return render(request, 'inventory/status_check.html', context)
@login_required
def item_details(request, pk):
    # Removed 'category' from select_related here, as it's not a ForeignKey
    item = get_object_or_404(InventoryItem.objects.select_related('location', 'project'), pk=pk)
    log_entries = InventoryLog.objects.filter(item=item).order_by('-timestamp')
    context = {
        'item': item,
        'log_entries': log_entries
    }
    return render(request, 'inventory/item_details.html', context)


# ---------------- Excel Export ----------------

@login_required
def export_inventory_excel(request):
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    filename = f"inventory_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventory Data"

    headers = [
        "Item Name", "UID No", "Serial Number", "Quantity",
        "Location", "Status", "Description", "Project", "Added By", "Date Added",
        "Last Modified", "CPU", "GPU", "OS", "Installed Software"
    ]
    sheet.append(headers)

    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font

    # Removed 'category' from select_related here.
    items = InventoryItem.objects.all().select_related('location', 'project', 'added_by').order_by('item_name')
    for item in items:
        row_data = [
            item.item_name,
            # item.category.name if item.category else 'N/A', # If category is CharField, this will be item.category
            item.uid_no,
            item.serial_number if item.serial_number else 'N/A',
            item.quantity,
            item.location.name if item.location else 'N/A',
            item.status,
            item.description if item.description else 'N/A',
            item.project.name if item.project else 'N/A',
            item.added_by.username if item.added_by else 'N/A',
            item.date_added.strftime('%Y-%m-%d %H:%M:%S'),
            item.last_modified.strftime('%Y-%m-%d %H:%M:%S'),
            item.cpu if item.cpu else 'N/A',
            item.gpu if item.gpu else 'N/A',
            item.os if item.os else 'N/A',
            item.installed_software if item.installed_software else 'N/A'
        ]
        sheet.append(row_data)

    workbook.save(response)

    create_log_entry(request.user, None, 'exported', f"Inventory data exported to Excel by {request.user.username}.", uid_number_for_log='N/A')
    messages.success(request, "Inventory data exported to Excel successfully!")
    return response

@login_required
def transfer_items_to_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"transfer_template_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Transfer Template"

    headers = ["UID No", "New Location (Name)", "Project (Name, Optional)", "Remarks"]
    sheet.append(headers)

    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font

    workbook.save(response)
    create_log_entry(request.user, None, 'exported', "Transfer Excel template generated.", uid_number_for_log='N/A')
    messages.success(request, "Transfer Excel template generated successfully!")
    return response

@login_required
@require_POST
def transfer_inventory_items(request):
    try:
        data = json.loads(request.body)
        items_to_transfer_data = data.get('items', [])

        if not items_to_transfer_data:
            return JsonResponse({'success': False, 'message': 'No items provided for transfer.'}, status=400)

        transferred_count = 0
        failed_items = []

        with transaction.atomic():
            for item_data in items_to_transfer_data:
                item_id = item_data.get('id')
                new_location_id = item_data.get('new_location')
                project_id = item_data.get('project_id')

                if not item_id or not new_location_id:
                    failed_items.append({'id': item_id, 'reason': 'Missing item ID or new location ID'})
                    continue

                try:
                    item = InventoryItem.objects.select_for_update().get(id=item_id)
                    old_location = item.location.name if item.location else 'N/A'
                    old_project = item.project.name if item.project else 'N/A'

                    new_location = Location.objects.get(id=new_location_id)
                    new_project = None
                    if project_id:
                        new_project = Project.objects.get(id=project_id)

                    item.location = new_location
                    item.status = 'Assigned'
                    item.project = new_project

                    item.save()
                    transferred_count += 1

                    log_details = (f"Item '{item.item_name}' (UID: {item.uid_no}) transferred "
                                   f"from '{old_location}' to '{new_location.name}'. "
                                   f"Project changed from '{old_project}' to '{new_project.name if new_project else 'N/A'}'. "
                                   f"Status set to '{item.status}'.")
                    create_log_entry(request.user, item, 'transferred', log_details, uid_number_for_log=item.uid_no)

                except InventoryItem.DoesNotExist:
                    failed_items.append({'id': item_id, 'reason': f"Item with ID {item_id} not found."})
                except Location.DoesNotExist:
                    failed_items.append({'id': item_id, 'reason': f"New location with ID {new_location_id} not found."})
                except Project.DoesNotExist:
                    failed_items.append({'id': item_id, 'reason': f"Project with ID {project_id} not found."})
                except Exception as e:
                    failed_items.append({'id': item_id, 'reason': f"Error: {str(e)}"})
                    logger.exception(f"Error processing item {item_id} for transfer.")

        if transferred_count > 0:
            success_message = f'Successfully transferred {transferred_count} asset(s).'
            if failed_items:
                success_message += f' However, {len(failed_items)} item(s) failed to transfer.'
                messages.warning(request, success_message)
                return JsonResponse({'success': True, 'message': success_message, 'failed_items': failed_items})
            else:
                messages.success(request, success_message)
                return JsonResponse({'success': True, 'message': success_message})
        else:
            message = 'No assets were successfully transferred. Please check for errors.'
            messages.error(request, message)
            return JsonResponse({'success': False, 'message': message, 'failed_items': failed_items}, status=400)

    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON request.')
        return JsonResponse({'success': False, 'message': 'Invalid JSON request.'}, status=400)
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        logger.exception("An unexpected error occurred in transfer_inventory_items.")
        return JsonResponse({'success': False, 'message': f'An unexpected error occurred: {str(e)}'}, status=500)


# ---------------- Logs View ----------------
@login_required
def inventory_logs(request):
    # CORRECTED: Removed 'item__category' from select_related
    logs = InventoryLog.objects.all().select_related('user', 'item__location', 'item__project').order_by('-timestamp')

    context = {
        'logs': logs
    }
    return render(request, 'inventory/logs.html', context)