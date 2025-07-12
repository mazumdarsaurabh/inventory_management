# inventory_management/inventory/urls.py

from django.urls import path
from . import views

app_name = 'inventory' # THIS IS CRUCIAL FOR NAMESPACING

urlpatterns = [
    # Dashboard view - Renamed from dashboard_view to dashboard
    path('', views.dashboard_view, name='dashboard'),

    path('add/', views.add_item, name='add_item'),

    # Deletion views:
    # 1. Delete specific item by its primary key (from dashboard or item details)
    path('delete/<int:pk>/', views.delete_item_by_pk, name='delete_item_by_pk'),
    # 2. Delete item by UID (general form)
    path('delete_item_general/', views.delete_item_general, name='delete_item_general'),

    # Status check views:
    # 1. Status check by UID (general form, renamed for clarity)
    path('status_check/', views.status_check, name='status_check'),
    # 2. Display specific item details by primary key (e.g., from dashboard click)
    path('item_details/<int:pk>/', views.item_details, name='item_details'), # Renamed for clarity

    # User Authentication views:
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'), # Renamed from 'register'
    path('logout/', views.user_logout, name='logout'),

    # Item Modification views:
    # 1. Initial search for item by UID for modification (renamed for clarity)
    path('modify_item_search/', views.modify_item, name='modify_item_search'),
    # 2. Actual edit page for an item by its primary key
    path('edit/<int:pk>/', views.edit_item, name='edit_item'),

    # Excel Export views:
    path('export/', views.export_inventory_excel, name='export_inventory_excel'),
    # Note: transfer_items_to_excel was for generating an Excel to fill out manually.
    # The AJAX transfer handles updates directly now. You might keep this if you still need it.
    path('transfer-items-to-excel/', views.transfer_items_to_excel, name='transfer_items_to_excel'),

    # Inventory Transfer view (AJAX POST endpoint)
    path('transfer/', views.transfer_inventory_items, name='transfer_inventory_items'),

    # NEW: Logs View
    path('logs/', views.inventory_logs, name='inventory_logs'),
]