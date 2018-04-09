# Django imports
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Cross-app imports
from dot_basic.models import models as basic_models

# Models below

class Document(models.Model):
    description = models.CharField(max_length=255, blank=True)
    document = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Product(models.Model):
    user = models.ForeignKey(User, related_name="buyer", on_delete=models.CASCADE)
    name = models.CharField(max_length=140, null=True, blank=True)
    p_id = models.CharField(max_length=30, null=True, blank=True)
    p_type = models.CharField(max_length=30, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    currency = models.CharField(max_length=30, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    url = models.CharField(max_length=300, blank=True, null=True)

class CampaignItem(models.Model):
    user = models.ForeignKey(User, related_name='campaign_seller', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='campaign_item', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    currency = models.CharField(max_length=30, null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
