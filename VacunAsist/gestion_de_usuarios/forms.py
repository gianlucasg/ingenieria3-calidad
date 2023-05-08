
from django import forms
from django.contrib.auth.forms import UserCreationForm
from datetime import date
from django.http import request
from gestion_de_usuarios.models import *
from django.core.exceptions import ValidationError
from VacunAsist.settings import DATE_INPUT_FORMATS
import requests
import re
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Usuario



class FormularioDeRegistro (UserCreationForm):
    mensaje_riesgo = """¿Posee una o más de las siguientes condiciones?
    - Paciente oncológico
    - Persona trasplantada
    - Diabetes
    - Enfermedad Renal Crónica
    - Enfermedades Cardiovasculares
    - Enfermedades Respiratorias Crónicas"""
    dni =  forms.CharField(max_length = 8, min_length = 7, label = "DNI")
    email = forms.EmailField(label = "Email")
    nombre_apellido = forms.CharField(max_length = 50, label = "Nombre y apellido")
    sexo = forms.ChoiceField(label = "Sexo (Como figura en el DNI)", choices = (("M", "Masculino"),("F", "Femenino")))
    de_riesgo = forms.ChoiceField(label = "De riesgo", choices = (("1", "Si"), ("0", "No")), widget = forms.RadioSelect(attrs = {'class' : 'form-check-inline'}), help_text = mensaje_riesgo)
    password1 = forms.CharField(label = "Contraseña", widget = forms.PasswordInput, label_suffix = "contraseña")
    password2 = forms.CharField(label = "Repita su contraseña", widget = forms.PasswordInput)
    fecha_nacimiento  = forms.DateField(label = "Fecha de nacimiento", widget = forms.SelectDateWidget(years = range(date.today().year-110, date.today().year)), input_formats = DATE_INPUT_FORMATS)
    vacunatorio_pref = forms.ModelChoiceField(label = "Vacunatorio de preferencia", queryset = Vacunatorio.objects.all(), widget = forms.Select, empty_label = None)
    numero_tramite = forms.CharField(max_length = 11, label = "Numero de tramite", help_text = "Campo necesario para validar su identidad")
    field_order = ['dni', 'numero_tramite', 'nombre_apellido', 'sexo',"fecha_nacimiento", "email", "password1", "password2", "vacunatorio_pref", "de_riesgo"]
   
    class Meta:
       model = Usuario
       fields = ('dni', 'numero_tramite', 'nombre_apellido', 'sexo', "fecha_nacimiento", "email", "password1", "vacunatorio_pref", "de_riesgo")
   


    
    

    

    def clean_dni(self):

        dni = self.cleaned_data["dni"]
        new = Usuario.objects.filter(dni = dni)  
        if new.count():  
            raise ValidationError("Ya existe una cuenta con el DNI. Probá con otro.")  
        return dni
        

    def clean_fecha_nacimiento(self):

        fecha_nacimiento = self.cleaned_data['fecha_nacimiento']
        today = date.today()
        if (fecha_nacimiento) > (today):
            raise forms.ValidationError('Ingresá una fecha válida.')
        
        return fecha_nacimiento

    def clean_email(self):  

        email = self.cleaned_data['email'].lower()  
        return email  
  
    def clean_password2(self):  

        password1 = self.cleaned_data['password1']  
        password2 = self.cleaned_data['password2'] 
        if not bool(re.search(r'\d', password1)):
            raise ValidationError("La contraseña debe contener por lo menos un dígito.")
        if not bool(re.search('[a-zA-Z]', password1)):
            raise ValidationError("La contraseña debe contener por lo menos una letra.")
        if not(password1 and password2 and password1 == password2):  
            raise ValidationError("Las contraseñas no coinciden.")  
        return password2  

    def clean_riesgo(self):

        de_riesgo = self.cleaned_data['de_riesgo']
        return de_riesgo

    
    def clean_nombre_apellido(self):

        nombre_apellido = self.cleaned_data['nombre_apellido']
        return nombre_apellido

    def clean(self):
        
        if self.is_valid():
            dni = self.cleaned_data['dni']
            numero_tramite = self.cleaned_data['numero_tramite']
            sexo = self.cleaned_data["sexo"]
            persona = {"dni":dni,
                "tramite": numero_tramite,
                "sexo": sexo}
            headers = {
                'X-Api-Key': 'JhKDui9uWt63sxGsdE1Xw1pGisfKpjZK1WJ7EMmy',
                'Content-Type' : "application/json"
                }
            try:
                response = requests.post("https://hhvur3txna.execute-api.sa-east-1.amazonaws.com/dev/person/validate", 
                headers = headers, json = persona)
            except:
                raise ValidationError("Hubo un fallo en la conexión con el servidor. Vuelva a intentarlo más tarde.")
            else:
                if (response.status_code == 403):
                    raise ValidationError("Hubo un fallo en la conexión con el servidor. Vuelva a intentarlo más tarde.")
                if (response.status_code != 200):
                    raise ValidationError("Error de validación. Verifique que sus datos sean correctos e intente de nuevo.")

    def save(self, clave_alfanumerica, commit = True):
        user = Usuario.objects.crear_usuario(  
            self.cleaned_data['dni'],  
            self.cleaned_data['nombre_apellido'],  
            self.cleaned_data['sexo'],
            self.cleaned_data['email'],
            self.cleaned_data['de_riesgo'],
            self.cleaned_data['fecha_nacimiento'] ,
            clave_alfanumerica,
            self.cleaned_data['vacunatorio_pref'],
            self.cleaned_data['password1']
        )  
        return user

    
        

    

class FormularioDeAutenticacion(forms.ModelForm):
    
    dni =  forms.CharField(max_length = 8, label = "DNI")
    password = forms.CharField(label = "Contraseña", widget = forms.PasswordInput, label_suffix = "contraseña")
    clave_alfanumerica = forms.CharField(label = "Clave alfanumérica", max_length = 5)

    class Meta:
        model = Usuario
        fields = ("dni", "password", "clave_alfanumerica")
   
    def clean(self):

        if self.is_valid():
            dni = self.cleaned_data['dni']
            password = self.cleaned_data['password']
            clave_alfanumerica = self.cleaned_data['clave_alfanumerica']
            try:
                user = Usuario.objects.get(dni = dni)
            except Usuario.DoesNotExist:
                raise ValidationError("El DNI ingresado no se encuentra registrado en el sistema.")
            if not(user.check_password(password) and (user.clave_alfanumerica == clave_alfanumerica)):
                raise forms.ValidationError("DNI y/o contraseñas inválidas")
    
    
