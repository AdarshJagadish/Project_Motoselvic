# Generated by Django 5.1.4 on 2025-01-14 21:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='bike',
            field=models.ForeignKey(default='null', on_delete=django.db.models.deletion.CASCADE, to='app.bike'),
        ),
        migrations.AlterField(
            model_name='product',
            name='company',
            field=models.ForeignKey(default='null', on_delete=django.db.models.deletion.CASCADE, to='app.company'),
        ),
    ]
