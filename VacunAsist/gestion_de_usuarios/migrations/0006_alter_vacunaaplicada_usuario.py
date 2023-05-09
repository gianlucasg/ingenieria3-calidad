# Generated by Django 4.0.3 on 2022-06-17 04:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_de_usuarios', '0005_alter_vacunador_usuario'),
    ]

    operations = [
        migrations.AlterField(
            model_name = 'vacunaaplicada',
            name = 'usuario',
            field = models.ForeignKey(
                db_constraint=False, 
                on_delete=django.db.models.deletion.DO_NOTHING, 
                to=settings.AUTH_USER_MODEL),
        ),
    ]
