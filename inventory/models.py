from django.db import models
class InventoryItem(models.Model):
    category = models.CharField(max_length=100)
    item_name = models.CharField(max_length=255)
    uid_no = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100)
    quantity = models.IntegerField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    document = models.FileField(upload_to='documents/', blank=True, null=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)  # ✅ Add this line

    def __str__(self):
        return self.item_name