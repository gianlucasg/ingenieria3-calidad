# Generated by Django 4.0.4 on 2022-05-23 18:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_de_usuarios', 
        '0003_alter_inscripcion_options_alter_usuario_options_and_more'
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name = 'usuario',
            name = 'password',
            field = models.CharField(
                max_length=50, 
                null=True, 
                verbose_name='contrasenia'),
        ),
    ]
