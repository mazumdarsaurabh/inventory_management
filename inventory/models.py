# inventory/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid # While imported, it's not directly used for UID generation in the current logic.
             # You might remove it if not used elsewhere, or keep it if future plans involve UUIDs.
from django.db import transaction # Essential for atomic operations in UID generation
from django.db.models import F # Essential for atomic increments in UID generation

class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        # Optional: Add verbose names for better display in Django Admin
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ['name'] # Optional: Order locations by name by default

    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['name'] # Optional: Order projects by name by default

    def __str__(self):
        return self.name

# NEW MODEL: UIDCategorySequence for managing sequential UIDs per category-month
class UIDCategorySequence(models.Model):
    category_prefix = models.CharField(max_length=10) # e.g., 'LAP', 'MON'
    year_month = models.CharField(max_length=4) # 'YYMM', e.g., '2507'
    last_sequence_number = models.PositiveIntegerField(default=0)

    class Meta:
        # Ensures that for a given category and month, there's only one sequence counter
        unique_together = ('category_prefix', 'year_month')
        verbose_name = "UID Category Sequence"
        verbose_name_plural = "UID Category Sequences"

    def __str__(self):
        return f"{self.category_prefix}-{self.year_month} (Last Seq: {self.last_sequence_number})"


class InventoryItem(models.Model):
    # Define CATEGORY_CHOICES for mapping item types to prefixes
    CATEGORY_CHOICES = [
        ('Laptop', 'LAP'),
        ('Monitor', 'MON'),
        ('Printer', 'PRN'),
        ('Server', 'SRV'),
        ('Networking Device', 'NET'),
        ('Desktop PC', 'DESK'), # Added for common asset type
        ('Software License', 'SWL'), # Example for non-physical asset
        ('Other', 'OTH'),
    ]
    # Add a field to select the category for the item - this will drive the UID prefix
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')

    item_name = models.CharField(max_length=255)
    # uid_no will be auto-generated based on the protocol, unique across all items
    uid_no = models.CharField(max_length=100, unique=True, blank=True, null=True)
    serial_number = models.CharField(max_length=255, blank=True, null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('In Use', 'In Use'),
        ('In Repair', 'In Repair'),
        ('Disposed', 'Disposed'),
        ('In Transit', 'In Transit'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Available')
    description = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='documents/', blank=True, null=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    # Specific hardware/software fields
    cpu = models.CharField(max_length=100, blank=True, null=True, verbose_name="CPU")
    gpu = models.CharField(max_length=100, blank=True, null=True, verbose_name="GPU")
    os = models.CharField(max_length=100, blank=True, null=True, verbose_name="Operating System")
    installed_software = models.TextField(blank=True, null=True, verbose_name="Installed Software")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        # Optional: Order items by creation date or UID
        ordering = ['-created_at', 'item_name']

    # Override save method to auto-generate uid_no based on the defined protocol
    def save(self, *args, **kwargs):
        # Only generate uid_no if it's a new instance (pk is None) or if uid_no is explicitly empty
        if not self.pk or not self.uid_no:
            current_date = timezone.now()
            year_month = current_date.strftime('%y%m') # YYMM format (e.g., '2507')

            # Get the category prefix based on the selected category
            # Use .get(key, default) for safe lookup
            category_prefix = dict(self.CATEGORY_CHOICES).get(self.category, 'OTH')

            with transaction.atomic():
                # Get or create the sequence object for this specific category and month
                # select_for_update() locks the row to prevent race conditions during increment
                sequence_obj, created = UIDCategorySequence.objects.select_for_update().get_or_create(
                    category_prefix=category_prefix,
                    year_month=year_month,
                    defaults={'last_sequence_number': 0} # Initialize if new
                )
                
                # Atomically increment the sequence number in the database
                # Using F() expression ensures a race-condition-free increment directly in the DB
                sequence_obj.last_sequence_number = F('last_sequence_number') + 1
                sequence_obj.save(update_fields=['last_sequence_number']) # Optimize by only updating the changed field
                sequence_obj.refresh_from_db() # Reload the object to get the updated value

                # Format the UID: [CATEGORY_PREFIX]-[YYMM]-[SEQUENCE_NUMBER]
                sequence_number_padded = str(sequence_obj.last_sequence_number).zfill(4) # Pad with leading zeros (e.g., 0001)
                self.uid_no = f"{category_prefix}-{year_month}-{sequence_number_padded}"

        super().save(*args, **kwargs)

    def __str__(self):
        # Prefer uid_no if available, otherwise fall back to item_name
        return f"{self.item_name} ({self.uid_no or 'N/A'})"


class InventoryLog(models.Model):
    ITEM_ACTION_CHOICES = [
        ('added', 'Added'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('transferred', 'Transferred'),
        ('status_change', 'Status Change'),
        ('assigned_to_project', 'Assigned to Project'), # Example of a more specific action
        ('unassigned_from_project', 'Unassigned from Project'),
        ('location_change', 'Location Change'),
    ]
    # *** CRITICAL CORRECTION APPLIED HERE (as noted by you previously) ***
    # Changed on_delete to models.SET_NULL and added null=True, blank=True
    # This ensures log entries persist if the related InventoryItem is deleted.
    item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    action = models.CharField(max_length=30, choices=ITEM_ACTION_CHOICES) # Increased max_length for new choices
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField(blank=True, null=True)
    # uid_no is also nullable, to store the UID of a deleted item.
    # This is crucial for maintaining a reference to the item even after deletion.
    uid_no = models.CharField(max_length=100, blank=True, null=True,
                              help_text="UID of the item at the time of the log. Preserved even if item is deleted.")
    
    # Optional: You might want to log old/new values for certain changes
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"
        ordering = ['-timestamp'] # Order logs by most recent first

    def __str__(self):
        # Use uid_no directly for __str__ if item is null (i.e., item has been deleted)
        # This makes the log entry meaningful even after the item is gone.
        item_identifier = self.uid_no if self.uid_no else (self.item.uid_no if self.item else 'Unknown Item')
        username = self.user.username if self.user else 'System'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {item_identifier} - {self.action} by {username}"