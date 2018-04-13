# Django imports
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Cross-app imports
from dot_corporate import models as corporate_models

# Models below

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='documents', default='media/avatar.jpg')
    USD = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    EUR = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    RON = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    default_payment = models.CharField(max_length=10, default='EUR')
    corporate =  models.BooleanField(default=False)
@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

class Card(models.Model):
    user = models.ForeignKey(User, related_name="card_set", on_delete=models.CASCADE)
    number = models.CharField(max_length=15, blank=True)
    csv = models.CharField(max_length=3, blank=True)
    exp_date = models.CharField(max_length=5, null=True, blank=True)
    name = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15)
    provider = models.CharField(max_length=20, blank=True)
    c_currency = models.CharField(max_length=10, blank=True, null=True)

class Friendship(models.Model):
    creator = models.ForeignKey(User, related_name="friendship_creator_set", on_delete=models.CASCADE)
    friend = models.ForeignKey(User, related_name="friend_set", on_delete=models.CASCADE)
    status = models.CharField(max_length=30, blank=True, default='sent')

class Order(models.Model):
    user = models.CharField(max_length=30, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    home_currency = models.CharField(max_length=30, blank=True)
    home_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=3)
    target_currency = models.CharField(max_length=30, blank=True)
    target_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, default='pending')
    target_backup = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    home_backup = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)

class CompleteOrders(models.Model):
    user = models.CharField(max_length=30, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    home_currency = models.CharField(max_length=30, blank=True)
    home_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=3)
    target_currency = models.CharField(max_length=30, blank=True)
    target_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, default='complete')

class Notification(models.Model):
    user = models.ForeignKey(User, related_name="notification_set", on_delete=models.CASCADE)
    notification = models.CharField(max_length=30, blank=True)
    notification_type = models.CharField(max_length=30, blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    user2 = models.ForeignKey(User, related_name="notification_friend", blank=True, null=True, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, default="unseen")


class Message(models.Model):
    user_from = models.ForeignKey(User, related_name="users_from", on_delete=models.CASCADE)
    user_to = models.ForeignKey(User, related_name="users_to", on_delete=models.CASCADE)
    message = models.CharField(max_length=140, blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    date_seen = models.DateField(null=True, blank=True)
    time_seen = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, default="sending")
    status_back = models.CharField(max_length=10, default="sending")
    status_final = models.CharField(max_length=10, default="sending")

class PurchasedItem(models.Model):
    user = models.ForeignKey(User, related_name="item_buyer", on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name="seller", on_delete=models.CASCADE)
    name = models.CharField(max_length=140, null=True, blank=True)
    p_id = models.CharField(max_length=30, null=True, blank=True)
    p_type = models.CharField(max_length=30, null=True, blank=True)
    dj_id = models.CharField(max_length=30, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    currency = models.CharField(max_length=30, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    url = models.CharField(max_length=300, blank=True, null=True)

class Post(models.Model):
    user = models.ForeignKey(User, related_name="poster", on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    link = models.CharField(max_length=100, null=True, blank=True)

class OpHistory(models.Model):
    user = models.ForeignKey(User, related_name="user", on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name="receiver", null =True, on_delete=models.CASCADE)
    currency = models.CharField(max_length=30, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    optype = models.CharField(max_length=30, null=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)

class TransferHistory(models.Model):
    user = models.ForeignKey(User, related_name="User_Transfer_From", on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name="User_Transfer_To", null =True, on_delete=models.CASCADE)
    currency = models.CharField(max_length=30, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)

class Cart(models.Model):
    user = models.ForeignKey(User, related_name="cart_user", on_delete=models.CASCADE)
    product = models.ForeignKey(corporate_models.Product, related_name="cart_product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
