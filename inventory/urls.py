# inventory/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_item, name='add_item'),

    # 1. Update this for per-row delete:
    path('delete/<int:pk>/', views.delete_item, name='delete_item'), # This is for delete based on PK (from table rows)

    # 2. Add this for the general delete form (if you use a top button for it):
    path('delete_item/', views.delete_item_general, name='delete_item_general'), # This is for the general delete form

    # Same logic applies to status:
    path('status/<int:pk>/', views.status_item, name='status_item'), # For status based on PK (from table rows)
    path('status_item/', views.status_item_general, name='status_item_general'), # For the general status form

    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),

    # This is for the general modify form (search by UID)
    path('modify_item/', views.modify_item, name='modify_item'),

    # This is for editing a specific item by its primary key
    # Make sure your edit_item view accepts 'pk' (which it does in the last views.py)
    path('edit/<int:pk>/', views.edit_item, name='edit_item'), # Changed <str:uid> to <int:pk>

    # Export (make sure name matches what's in base.html)
    path('export/', views.export_inventory_excel, name='export_inventory_excel'), # Changed name to _excel as per previous fix
]