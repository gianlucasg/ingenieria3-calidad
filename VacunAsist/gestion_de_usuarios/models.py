from django.db import models
from datetime import date
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager



class MyAccountManager(BaseUserManager):

    def crear_usuario(self, dni, nombre_apellido, sexo, email, de_riesgo, fecha_nacimiento, clave_alfanumerica, vacunatorio_pref, password):
        """Crea un usuario con el dni"""
        values = [dni, nombre_apellido, sexo, email, de_riesgo, fecha_nacimiento, clave_alfanumerica, vacunatorio_pref, password]
        dicci_campos = dict(zip(self.model.REQUIRED_FIELDS, values))
        for nombre_campo, valor in dicci_campos.items():
            if not valor: #VALOR == NULL
                raise ValueError(f"El valor {nombre_campo} debe ser especificado")

        user = self.model(
            dni = dni,
            email = self.normalize_email(email),
            nombre_apellido = nombre_apellido,
            sexo = sexo,
            de_riesgo = de_riesgo,
            fecha_nacimiento = fecha_nacimiento,
            clave_alfanumerica = clave_alfanumerica,
            vacunatorio_pref = vacunatorio_pref,
            password = password,
            rol_actual = "Ciudadano"
            )
        user.set_password(password)
        user.save(using = self._db)
        return user
    
    def crear_administrador(self, dni, nombre_apellido, sexo, email, de_riesgo, fecha_nacimiento, clave_alfanumerica, vacunatorio_pref, password):
        user = self.model(
            dni = dni,
            email = self.normalize_email(email),
            nombre_apellido = nombre_apellido,
            sexo = sexo,
            de_riesgo = de_riesgo,
            fecha_nacimiento = fecha_nacimiento,
            clave_alfanumerica = clave_alfanumerica,
            vacunatorio_pref = vacunatorio_pref,
            )
        user.es_administrador = True
        user._is_superuser = True
        user.es_vacunador = False

        user.save(using = self._db)
        return user


class Usuario(AbstractBaseUser):
    es_vacunador = models.BooleanField(default = False)
    es_administrador = models.BooleanField(default = False)
    _is_superuser = models.BooleanField(default = False)
    dni = models.CharField(unique = True, max_length = 8, primary_key = True)
    nombre_apellido = models.CharField(max_length = 50)
    opciones_sexo = [("F", "Femenino"), ("M", "Masculino")]
    sexo = models.CharField(max_length = 1, choices = opciones_sexo)
    email = models.EmailField()
    de_riesgo = models.BooleanField(default = False)
    fecha_nacimiento = models.DateField()
    password = models.CharField(null = True, max_length = 50, verbose_name = 'contrasenia')  #ver max_length por hashing/encriptacion
    clave_alfanumerica = models.CharField(max_length = 5)
    vacunatorio_pref = models.ForeignKey("Vacunatorio", on_delete = models.SET_NULL, null = True) #deberiamos cambiar las HU en tal caso, noguta
    rol_actual = models.CharField(max_length = 20, default = None ,blank = True, null = True)

    class Meta:
        verbose_name_plural = "Usuarios"
        app_label = 'gestion_de_usuarios'

    objects = MyAccountManager()
    
    
    USERNAME_FIELD = "dni"
    REQUIRED_FIELDS = ['nombre_apellido', 'sexo', 'fecha_nacimiento', 'email', 'de_riesgo', 'vacunatorio_pref']


    def __str__(self):
        return self.dni, self.get_full_name()

    def get_full_name(self):
        return self.nombre_apellido
    
    def get_email(self):
        return self.email
  

class Vacuna(models.Model):
    tipo = models.CharField(max_length = 20)
    
    inscriptos = models.ManyToManyField(Usuario, related_name = "campañas_inscriptas", 
    through = "Inscripcion",
    through_fields = ("vacuna", "usuario"),
    default = None,
    blank = True)
    
    tienen_aplicaciones = models.ManyToManyField(Usuario, related_name = "vacunas_aplicadas", 
    through = "VacunaAplicada",
    through_fields = ("vacuna", "usuario"),
    default = None,
    blank = True)

    
class Vacunatorio(models.Model):
    nombre = models.CharField(max_length = 30)
    direccion = models.CharField(max_length = 25)
    email = models.EmailField()
    numero_telefono = models.CharField(max_length = 20)
    vacunas_en_stock = models.ManyToManyField(Vacuna, related_name = "vacunatorios_con_stock", 
    through = "VacunaVacunatorio",
    through_fields = ("vacunatorio", "vacuna"),
    default = None,
    blank = True)

    def __str__(self) -> str:
        return self.nombre


class Vacunador(models.Model):
    usuario = models.OneToOneField(Usuario, related_name = "vacunador", on_delete = models.CASCADE)
    vacunatorio_de_trabajo = models.ForeignKey(Vacunatorio, on_delete = models.PROTECT)

    class Meta:
        verbose_name_plural = "Vacunadores"

    def __str__(self):
        return str(self.user)
       

class Inscripcion(models.Model):
    class Meta:
        verbose_name_plural = "Inscripciones"
        
    usuario = models.ForeignKey(Usuario, on_delete = models.SET_NULL, null = True) #decidir
    fecha = models.DateField(blank = True, null = True)
    vacunatorio = models.ForeignKey(Vacunatorio, on_delete = models.PROTECT)  #decidir
    vacuna = models.ForeignKey(Vacuna, on_delete = models.PROTECT) #decidir


class VacunaAplicada(models.Model):
    class Meta: 
        unique_together = ("usuario", "vacuna")
        verbose_name_plural = "Vacunas_aplicadas"
    usuario = models.ForeignKey("Usuario", on_delete = models.DO_NOTHING, db_constraint = False)
    vacuna = models.ForeignKey(Vacuna, on_delete = models.DO_NOTHING)
    vacunatorio = models.ForeignKey(Vacunatorio, on_delete = models.DO_NOTHING, default = None)
    fecha = models.DateField(default = date.today)
    marca = models.CharField(max_length = 20, blank = True, null = True)
    lote = models.CharField(max_length = 20, blank = True, null = True)
    con_nosotros = models.BooleanField()

class VacunasNoAplicadas(models.Model):
    class Meta: 
        verbose_name_plural = "Vacunas_pospuestas"
    usuario = models.ForeignKey("Usuario", on_delete = models.DO_NOTHING, db_constraint = False)
    vacuna = models.ForeignKey(Vacuna, on_delete = models.DO_NOTHING)
    fecha = models.DateField()
    vacunatorio = models.ForeignKey(Vacunatorio, on_delete = models.DO_NOTHING)
    estado = models.CharField(max_length = 10)


class VacunaVacunatorio(models.Model):
    class Meta:
        unique_together = ("vacuna", "vacunatorio")
    vacuna = models.ForeignKey("Vacuna", on_delete = models.PROTECT)
    vacunatorio = models.ForeignKey("Vacunatorio", on_delete = models.PROTECT)
    stock_remanente = models.PositiveIntegerField()