# Generated by Django 5.1.7 on 2025-06-09 06:36

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_review_updated_at_alter_review_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='is_active',
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, default=django.utils.timezone.now, max_length=15),
            preserve_default=False,
        ),
    ]
