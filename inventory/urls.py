from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_item, name='add_item'),
    path('delete/', views.delete_item, name='delete_item'),
    path('status/', views.status_item, name='status_item'),  # ✅ This line is important
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('modify/', views.modify_item, name='modify_item'),
    path('edit/<str:uid>/', views.edit_item, name='edit_item'),
    path('export/', views.export_inventory_excel, name='export_inventory'),
]