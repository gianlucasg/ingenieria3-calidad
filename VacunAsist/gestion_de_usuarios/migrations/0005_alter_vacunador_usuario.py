# Generated by Django 4.0.3 on 2022-05-27 21:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_de_usuarios', '0004_alter_usuario_password'),
    ]

    operations = [
        migrations.AlterField(
            model_name = 'vacunador',
            name = 'usuario',
            field = models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='vacunador', to=settings.AUTH_USER_MODEL),
        ),
    ]
