# Generated by Django 2.0.4 on 2018-04-13 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dot_basic', '0004_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='default_payment',
            field=models.CharField(default='EUR', max_length=10),
        ),
    ]
