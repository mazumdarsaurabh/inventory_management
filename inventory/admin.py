# inventory_management/inventory/admin.py

from django.contrib import admin
# Make sure to import Location, InventoryItem, Project, and the new InventoryLog
from .models import Location, InventoryItem, Project, InventoryLog

# Register your models here.
admin.site.register(Location)
admin.site.register(InventoryItem)
admin.site.register(Project)
admin.site.register(InventoryLog)  # <--- THIS IS THE CORRECTION: Register the new log model