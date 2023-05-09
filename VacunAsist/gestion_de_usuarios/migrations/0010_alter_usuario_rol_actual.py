# Generated by Django 4.0.5 on 2022-07-04 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_de_usuarios', '0009_alter_usuario_rol_actual'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='rol_actual',
            field=models
                .CharField(
                    blank=True, 
                    choices=[
                        ('Vac', 'Vacunador'), 
                        ('Adm', 'Administrador'), 
                        ('User', 'Usuario comun')], 
                    max_length=4, 
                    null=True),
        ),
    ]
