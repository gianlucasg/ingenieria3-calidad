from datetime import date
from time import time
from django.http import HttpResponse
import numpy as np
from django.shortcuts import render, redirect, HttpResponse
from django.template import loader
from gestion_de_usuarios.models import (Inscripcion, 
    VacunaAplicada, 
    Vacuna, 
    Vacunatorio, 
    VacunaVacunatorio, 
    Vacunador, 
    VacunasNoAplicadas)
from gestion_de_usuarios.forms import (
    FormularioDeRegistro, 
    FormularioDeAutenticacion)
from django.contrib.auth import login, authenticate, logout
from gestion_de_usuarios.models import Usuario
import plotly.express as px
import random, string
from django.core.mail import send_mail
from VacunAsist.settings import EMAIL_HOST_USER
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
import pdfkit
import itertools
import mimetypes
import os
from pathlib import Path
import requests
import json
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dateutil.relativedelta import relativedelta

User = get_user_model()

def home(request):

    if request.user.is_authenticated:
        context = dict.fromkeys(["user", "rol", "covid", "fiebre_amarilla", 
            "gripe", "mensaje", "titulo", "vacuna_fa"], "No")
        user = request.user
        if (user.rol_actual != "Ciudadano"):
            return redirigir_por_rol(request)
        context["user"] = user
        context["mensaje"] = request.session.get('mensaje', "")
        context["titulo"] = request.session.get('titulo', "")
        request.session["mensaje"] = ""
        request.session["titulo"] = ""

        inscripciones = Inscripcion.objects.filter(usuario = user)
        covid = (inscripciones
            .filter(vacuna = Vacuna
            .objects
            .filter(tipo = "COVID-19").first())) #ARREGLAR
        fiebre_amarilla = (inscripciones
            .filter(vacuna = Vacuna
                .objects
                .filter(tipo = "Fiebre_amarilla")
                .first()))
        vacuna_fa = (VacunaAplicada
            .objects
            .filter(usuario = user, vacuna = Vacuna
                .objects
                .filter(tipo = "Fiebre_amarilla")
                .first(),con_nosotros = True))
        gripe = (inscripciones
            .filter(vacuna = Vacuna.objects.filter(tipo = "Gripe").first()))
        if(vacuna_fa):
            context["vacuna_fa"] = "Si"
        if (covid):
            context["covid"] = "Si"
        if (fiebre_amarilla):
            context["fiebre_amarilla"] = "Si"
        if (gripe):
            context["gripe"] = "Si"

    

        return render(request, "home.html", context)

    return redirect('Index')    


@login_required
def visualizar_stock_administrador(request):
    user = request.user
    if (user.rol_actual != "Administrador"):
        return redirigir_por_rol(request)

    context = dict.fromkeys(["vacunas", "mensaje"], "")

    context["sobrante"] = len(Inscripcion
        .objects
        .filter(fecha__lt = date.today()))
    context["vacunas"] = VacunaVacunatorio.objects.all()
    context["mensaje"] = request.session.get('mensaje', "")
    request.session["mensaje"] = ""
    #ver si contemplar esto

    #cambiar return
    return render(request, 'vacunas_adm.html', context)

def redirigir_por_rol(request):
    user = request.user
    if (user.rol_actual == "Ciudadano"):
        return redirect(home)
    elif (user.rol_actual == "Vacunador"):
        return redirect(ver_turnos_del_dia)
    else:
        return redirect(visualizar_stock_administrador)

def get_redirect_if_exists(request):
    redirect = None
    if request.GET:
        if request.GET.get("next"):
            redirect = str(request.GET.get("next"))
    return redirect

def registrar(request):

    user = request.user
    if user.is_authenticated:
        return redirect("Home")

    context = {}
    if request.POST:
        form = FormularioDeRegistro(request.POST)
        if form.is_valid():
            clave_alfanum = ''.join(
                random.choices(string.ascii_letters + string.digits, k = 5)
            )
            form.save(clave_alfanum)
            dni = form.cleaned_data["dni"]
            password = form.cleaned_data["password1"]
            mail = request.POST.get('email')
            html_message = (loader
                .render_to_string('email_clave.html', 
                                  {'clave': clave_alfanum}))
            try:
                send_mail('Clave alfanumerica Vacunassist', "", 
                    EMAIL_HOST_USER, [mail], html_message = html_message)
            except:
                pass
            user = authenticate(dni = dni, password = password)
            login(request, user, 
                backend = 'django.contrib.auth.backends.ModelBackend')
            destination = get_redirect_if_exists(request)
            if destination: 
                return redirect(destination)
            return redirect("Home")
        else:
            context['registration_form'] = form

    else:
        form = FormularioDeRegistro()
        context['registration_form'] = form
    return render(request, 'registro.html', context)

@login_required
def cerrar_sesion(request):
    user = request.user
    usuario = Usuario.objects.get(dni = user.dni)
    usuario.rol_actual = ""
    usuario.save()
    logout(request)
    return redirect("Index")

@login_required
def ver_turnos_del_dia(request):
    user = request.user
    if (user.rol_actual != "Vacunador"):
        return redirigir_por_rol(request)
    context = request.session.get("context", {})
    if (context == {}):
        context["mensaje"] = request.session.get('mensaje', "")
    turnos = (Inscripcion
        .objects
        .filter(fecha = date.today())
        .filter(vacunatorio_id = user.vacunador.vacunatorio_de_trabajo))
    hoy = str(date.today())
    tipos = Vacuna.objects.all()
    
    if (context["mensaje"] == "") and (not turnos):
        context["mensaje"] = "No existen turnos asignados para el día de hoy."
    else:
        request.session["mensaje"] = ""

    if "registrado" not in context.keys():
        context["registrado"] = ""
    if "tipo_a_cargar" not in context.keys():
        context["tipo_a_cargar"] = ""

    request.session["context"] = {}
    context["turnos"] = turnos
    context["tipos"] = tipos
    context["today"] = hoy
    return render(request, "ver_turnos_hoy.html", context)

def iniciar_sesion(request, *args, **kwargs):
    context = dict.fromkeys(["adm","vac","roles","mensaje"], "")
    context["mensaje"] = request.session.get("mensaje", "")
    request.session["mensaje"] = ""
    user = request.user
    if user.is_authenticated: 
        return redirect("Home")

    if request.POST:
        form = FormularioDeAutenticacion(request.POST)
        if form.is_valid():
            dni = request.POST.get('dni')
            user = Usuario.objects.get(dni = dni)
            if user:
                login(request, user, 
                    backend = 'django.contrib.auth.backends.ModelBackend')
                if not(user.es_administrador) or not(user.es_vacunador) :
                    user.rol_actual = "Ciudadano"
                    user.save()
                    return redirect("Home")
                else:
                    context["roles"] = "si"
                    if user.es_administrador:
                        context["adm"] = "si"
                    if user.es_vacunador:
                        context["vac"] = "si"
                    return render(request, "Login.html", context)
        else:  
            context['login_form'] = form
    else:
        form = FormularioDeAutenticacion()
        context['login_form'] = form
    return render(request, "Login.html", context)


def iniciar_sesion_rol(request):
    rol = request.POST.get("rol")
    user = request.user
    usuario = Usuario.objects.get(dni = user.dni)
    usuario.rol_actual = rol
    usuario.save()
    if rol == "Administrador":
        return redirect("VacunasStock")
    elif rol == "Vacunador":
        return redirect(ver_turnos_del_dia)
    else:
        return redirect("Home")


@login_required
def buscar_turno(request):

    if request.POST:
        dni = request.POST["dni"]
        if dni:
            try:
                turno = Inscripcion.objects.get(usuario = dni)
            except Inscripcion.DoesNotExist:
                return HttpResponse("El dni ingresado no tiene turno.")
            else:
                return HttpResponse(turno)
    context = {}
    return render(request, "busqueda_turno.html", context)

@login_required
def descargar_certificado_fiebre_amarilla(request):
    options = {
        'dpi': 360,
        'page-size': 'A4',
        'margin-top': '0.0in',
        'margin-right': '0.0in',
        'margin-bottom': '0.0in',
        'margin-left': '0.0in',
        'encoding': "UTF-8",
        'custom-header': [
           ('Accept-Encoding', 'gzip')
        ],
        'no-outline': None,
    }
    config = pdfkit.configuration(
        wkhtmltopdf = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
    )
    context = dict.fromkeys("user", "vacuna")
    usuario = request.user
    context["user"] = usuario
    vacuna = (VacunaAplicada
        .objects
        .filter(usuario = usuario, 
            vacuna = Vacuna.objects.get(tipo = "Fiebre_amarilla"))
        .first())
    context["vacuna"] = vacuna
    filename = "certificado.pdf"
    path_certificado = os.path.normpath(os.path.join(Path(__file__), 
        os.pardir, os.pardir, "Vacunasist", "Vacunasist", "templates", 
        "CERTIFICADO-RENDER.html"))
    f = open(path_certificado, "w")
    html = loader.get_template("CERTIFICADO.html")
    html_content = html.render(context)
    f.write(html_content)
    f.close()

    certificado = pdfkit.from_file(path_certificado, output_path = None, 
        configuration = config, options = options)
    response = HttpResponse(certificado, content_type = mimetypes.guess_type)
    response["Content-Disposition"] = f"attachment; filename = {filename}"
    return response

@login_required
def buscar_dni(request): 

    context = dict.fromkeys(["dni", "nombre_apellido", "fecha_nacimiento", 
        "registrado", "mensaje"], "")
    dni = request.POST.get("Dni")
    usuario_registrado = Usuario.objects.filter(dni = dni).first()
    
    if (usuario_registrado):
        context["dni"] = dni
        context["nombre_apellido"] = usuario_registrado.nombre_apellido
        context["fecha_nacimiento"] = str(usuario_registrado.fecha_nacimiento)
        context["email"] = usuario_registrado.email
        context["registrado"] = "si"
        context["mensaje"] = None
        request.session["context"] = context
        return redirect(ver_turnos_del_dia)
    
    persona = {"dni": dni}
    headers = {
            'X-Api-Key': 'JhKDui9uWt63sxGsdE1Xw1pGisfKpjZK1WJ7EMmy',
            'Content-Type' : "application/json"
            }
    try:
        response = requests.post("https://hhvur3txna.execute-api.sa-east-1.\
amazonaws.com/dev/person/lookup", 
        headers = headers, json = persona)
    except:
        context["mensaje"] = "Hubo un fallo en la conexión con el servidor. \
Vuelva a intentarlo más tarde."
    else:
        if (response.status_code == 403):
            context["mensaje"] = "Hubo un fallo en la conexión con el \
servidor. Vuelva a intentarlo más tarde."
        if (response.status_code != 200):
            context["mensaje"] = "El DNI no esta asociado a un documento \
valido de la República Argentina."
        else:
            persona = response.content
            persona = json.loads(persona)
            context["dni"] = dni
            context["nombre_apellido"] = persona["apellido"]
            context["fecha_nacimiento"] = str(datetime
                    .strptime(persona["fechaNacimiento"][:10], "%Y-%m-%d")
                    .date())
            context["registrado"] = "no"
            context["mensaje"] = None
    request.session["context"] = context
    return redirect(ver_turnos_del_dia)

@login_required
def alta_vacunador(request):

    context = dict.fromkeys(["mensaje", "rol"], "")
    context["rol"] = "Vac"
    dni = request.POST.get("Dni")
    vacunatorio_trabajo = request.POST.get("VacunatorioTrabajo")
    usuario = Usuario.objects.filter(dni = dni).first()
    vacunatorio = (Vacunatorio
        .objects
        .filter(nombre = vacunatorio_trabajo)
        .first())
    if (usuario):
        if (usuario.es_vacunador):
            context["mensaje"] = "El usuario ya es un vacunador."
        else:
            usuario.es_vacunador = True
            vacunador = Vacunador(usuario = usuario, 
                vacunatorio_de_trabajo = vacunatorio)
            vacunador.save()
            usuario.vacunador = vacunador
            usuario.save()
            context["mensaje"] = "El vacunador ha sido dado de alta \
exitosamente."
    else:    
        context["mensaje"] = "El DNI ingresado no se encuentra registrado en \
el sistema"
    request.session["context"] = context
    return redirect(gestionar_usuarios_admin)

@login_required
def alta_administrador(request):

    context = dict.fromkeys(["mensaje", "rol"], "")

    dni = request.POST.get("Dni")
    usuario = Usuario.objects.filter(dni = dni).first()
    if (usuario):
        if (usuario.es_administrador):
            context["mensaje"] = "El usuario ya es un administrador."
        else:
            usuario.es_administrador = True
            usuario.save()
            context["mensaje"] = "El administrador ha sido dado de alta \
exitosamente."
    else:
        context["mensaje"] = "El DNI ingresado no se encuentra registrado en \
el sistema"
    request.session["context"] = context

    return redirect(gestionar_usuarios_admin)

@login_required
def gestionar_usuarios_admin(request):
    user = request.user
    if (user.rol_actual != "Administrador"):
        return redirigir_por_rol(request)
    context = request.session.get("context", {})
    request.session["context"] = {}
    if (context == {}):
        context["mensaje"] = request.session.get('mensaje', "")
        context["rol"] = ""
    
    vacunadores = Usuario.objects.filter(es_vacunador = True)
    administradores = Usuario.objects.filter(es_administrador = True)
    context["vacunadores"] = vacunadores
    context["admins"] = administradores
    context["vacunatorios"] = Vacunatorio.objects.all()
    return render(request, "gestionar_usuarios_admin.html", context)

@login_required
def visualizar_estadisticas(request):
    user = request.user
    if (user.rol_actual != "Administrador"):
        return redirigir_por_rol(request)
    context = dict.fromkeys([
        "mensaje", "grafico_poli", "grafico_corr", "grafico_hosp", 
        "grafico_total", "grafico_vacuna", "vacunatorios"], "")
    print(context["mensaje"])
    #Obtengo la fecha inicial y la fecha final de la pantalla
    fecha_inicial = request.GET.get("Fecha_ini")
    fecha_final = request.GET.get("Fecha_fin")
    print(fecha_inicial)
    print(fecha_final)

    #Cargo las vacunas aplicadas y no aplicadas en un df, 
    #corrijo valores y nombres de columnas
    vac_aplicadas = VacunaAplicada.objects.all().values()
    vac_aplicadas_df = pd.DataFrame(vac_aplicadas)
    pospuestas_y_canceladas = VacunasNoAplicadas.objects.all().values()
    vac_no_aplicadas_df = pd.DataFrame(pospuestas_y_canceladas)
    df_vacunas = vac_aplicadas_df.append(vac_no_aplicadas_df)
    df_vacunas["estado"] = (df_vacunas["estado"]
        .replace(to_replace = np.nan, value = "Aplicado"))
    df_vacunas['fecha'] = pd.to_datetime(df_vacunas['fecha'])
    df_vacunas['fecha'] = df_vacunas['fecha'] - pd.to_timedelta(7, unit = 'd')
    df_vacunas = df_vacunas.groupby([
            'vacuna_id', 'vacunatorio_id', 'estado', 
            pd.Grouper(key = 'fecha', freq = 'W-MON')
        ])(["id"]
        .count()
        .reset_index())
    df_vacunas.columns = ["Vacuna", "Vacunatorio", "Estado", "Semana", 
        "Cantidad"]

    #Si existe fecha inicial, comienzo las validaciones
    if (fecha_inicial):
        fecha_inicial = date.fromisoformat(fecha_inicial)
        print(fecha_inicial)
        fecha_final = date.fromisoformat(fecha_final)
        print(fecha_final)
        if (fecha_inicial < fecha_final) and (fecha_final <= date.today()):

            while (fecha_inicial.isocalendar().weekday != 1):
                fecha_inicial = fecha_inicial + timedelta(days =- 1)
            while (fecha_final.isocalendar().weekday != 1):
                fecha_final = fecha_final + timedelta(days = 1)
            inicio_minimo = fecha_final - timedelta(weeks = 3)
            if ((fecha_final - fecha_inicial) < (fecha_final - inicio_minimo)):
                context["mensaje"] = "Las fechas deben constituir \
por lo menos 4 semanas."
                
            print(fecha_inicial)
            print(fecha_final)
        else:
            context["mensaje"] = "Las fechas ingresadas son inválidas."
            
    # Sino, el rango de fechas es desde el día de hoy, 4 semanas 
    #hacia atrás.
    if (not fecha_inicial or context["mensaje"] != ""):
        fecha_final = date.today()
        fecha_inicial = fecha_final - timedelta(weeks = 3)
        while (fecha_inicial.isocalendar().weekday != 1):
            fecha_inicial = fecha_inicial + timedelta(days =- 1)
        while (fecha_final.isocalendar().weekday != 1):
            fecha_final = fecha_final + timedelta(days = 1)
        print(fecha_inicial)
        print(fecha_final)
    
    #df_vacunas = df_vacunas[df_vacunas["Semana"] >= fecha_inicial]
    #[df_vacunas["Semana"] <= fecha_final]

    

    

    tipos_vacunas = Vacuna.objects.all().values()
    tipos_dicci = dict()
    for tipo in tipos_vacunas:
        tipos_dicci.update({tipo["id"]: tipo["tipo"]}) 

    vacunatorios = Vacunatorio.objects.all().values()
    vacunatorios_dicci = dict()
    for vac in vacunatorios:
        vacunatorios_dicci.update({vac["id"]: vac["nombre"]}) 
    

    df_vacunas["Vacuna"] = (df_vacunas["Vacuna"]
        .replace(to_replace = tipos_dicci))
    df_vacunas["Vacunatorio"] = (df_vacunas["Vacunatorio"]
        .replace(to_replace = vacunatorios_dicci))


    tipos_vacunas = list(df_vacunas['Vacuna'].unique())
    vacunatorios = list(df_vacunas["Vacunatorio"].unique())
    semanas = list(df_vacunas["Semana"].unique())
    semana_actual = fecha_inicial
    while (semana_actual < date.today()):
        if (pd.to_datetime(semana_actual)) not in semanas:
            semanas.append(semana_actual)
        semana_actual = semana_actual + pd.to_timedelta(7, unit = 'd')
    estados = list(df_vacunas["Estado"].unique())

    combinaciones = list(itertools.product(tipos_vacunas, vacunatorios, 
        semanas, estados))
    df_vacunas = (df_vacunas
        .set_index(['Vacuna', 'Vacunatorio', "Semana",'Estado'])
        .reindex(combinaciones, fill_value = 0)
        .reset_index()
        .sort_values("Semana"))
    
    df_vacunas = df_vacunas[
        (df_vacunas["Semana"] >= pd.to_datetime(fecha_inicial)) 
        & (df_vacunas["Semana"] <= pd.to_datetime(fecha_final))
    ]

    df_polideportivo = (df_vacunas
        [df_vacunas["Vacunatorio"] == "Polideportivo"])
    df_corralon = (df_vacunas
        [df_vacunas["Vacunatorio"] == "Corralón Municipal"])
    df_hospital = (df_vacunas
        [df_vacunas["Vacunatorio"] == "Hospital 9 de julio"])

    fig = go.Figure()
    for estado in estados:
        for vacuna in tipos_vacunas:
            if (vacuna == "Gripe"):
                fig.add_trace(
                go.Scatter(
                x = (df_polideportivo['Semana']
                    [df_polideportivo["Estado"] == estado]
                    [df_polideportivo['Vacuna'] == vacuna]),
                y = (df_polideportivo['Cantidad']
                    [df_polideportivo["Estado"] == estado]
                    [df_polideportivo['Vacuna'] == vacuna]),
                name = estado, visible = True
                )
            )
            else:
                fig.add_trace(
                go.Scatter(
                x = (df_polideportivo['Semana']
                    [df_polideportivo["Estado"] == estado]
                    [df_polideportivo['Vacuna'] == vacuna]),
                y = (df_polideportivo['Cantidad']
                    [df_polideportivo["Estado"] == estado]
                    [df_polideportivo['Vacuna'] == vacuna]),
                name = estado, visible = False
                )
            )


    buttons = []

    for i, tipo in enumerate(tipos_vacunas):
        args = [False] * len(tipos_vacunas)
        args[i] = True

        button = dict(label = tipo,
                      method = "update",
                      args=[{"visible": args}])

        buttons.append(button)

    fig.update_layout(
        updatemenus=[dict(
                        active = 0,
                        type = "dropdown",
                        buttons = buttons,
                        x = 0,
                        y = 1.1,
                        xanchor = 'left',
                        yanchor = 'bottom'
                    )], 
        autosize = False,
        width = 1000,
        height = 800, 
        yaxis = dict(range = [-1, 9])      
    )

    context['grafico_poli'] = fig.to_html()

    fig = go.Figure()

    for estado in estados:
        for vacuna in tipos_vacunas:
            if (vacuna == "Gripe"):
                fig.add_trace(
                go.Scatter(
                    x = (df_corralon['Semana']
                        [df_corralon["Estado"] == estado]
                        [df_corralon['Vacuna'] == vacuna]),
                    y = (df_corralon['Cantidad']
                        [df_corralon["Estado"] == estado]
                        [df_corralon['Vacuna'] == vacuna]),
                    name = estado, visible = True
                )
            )
            else:
                fig.add_trace(
                go.Scatter(
                    x = (df_corralon['Semana']
                        [df_corralon["Estado"] == estado]
                        [df_corralon['Vacuna'] == vacuna]),
                    y = (df_corralon['Cantidad']
                        [df_corralon["Estado"] == estado]
                        [df_corralon['Vacuna'] == vacuna]),
                    name = estado, visible = False
                )
            )


    buttons = []

    for i, tipo in enumerate(tipos_vacunas):
        args = [False] * len(tipos_vacunas)
        args[i] = True

        button = dict(label = tipo,
                      method = "update",
                      args = [{"visible": args}])

        buttons.append(button)

    fig.update_layout(
        updatemenus = [dict(
                        active = 0,
                        type = "dropdown",
                        buttons = buttons,
                        x = 0,
                        y = 1.1,
                        xanchor = 'left',
                        yanchor = 'bottom'
                    )], 
        autosize = False,
        width = 1000,
       height = 800,
       yaxis = dict(range = [-1, 9]) 
    )

    context['grafico_corr'] = fig.to_html()

    fig = go.Figure()

    for estado in estados:
        for vacuna in tipos_vacunas:
            if (vacuna == "Gripe"):
                fig.add_trace(
                go.Scatter(
                    x = (df_hospital['Semana']
                        [df_hospital["Estado"] == estado]
                        [df_hospital['Vacuna'] == vacuna]),
                    y = (df_hospital['Cantidad']
                        [df_hospital["Estado"] == estado]
                        [df_hospital['Vacuna'] == vacuna]),
                    name = estado, visible = True
                )
            )
            else:
                fig.add_trace(
                go.Scatter(
                    x = (df_hospital['Semana']
                        [df_hospital["Estado"] == estado]
                        [df_hospital['Vacuna'] == vacuna]),
                    y = (df_hospital['Cantidad']
                        [df_hospital["Estado"] == estado]
                        [df_hospital['Vacuna'] == vacuna]),
                    name = estado, visible = False
                )
            )

    buttons = []

    for i, tipo in enumerate(tipos_vacunas):
        args = [False] * len(tipos_vacunas)
        args[i] = True

        button = dict(label = tipo,
                      method = "update",
                      args = [{"visible": args}])

        buttons.append(button)

    fig.update_layout(
        updatemenus=[dict(
                        active = 0,
                        type = "dropdown",
                        buttons = buttons,
                        x = 0,
                        y = 1.1,
                        xanchor = 'left',
                        yanchor = 'bottom'
                    )], 
        autosize = False,
        width = 1000,
       height = 800,
       yaxis = dict(range = [-1, 9]) 
    )

    context['grafico_hosp'] = fig.to_html()

    df_totales_por_vacuna = (df_vacunas
        .groupby(["Vacuna", "Estado", "Semana"])["Cantidad"]
        .sum()
        .reset_index())
    fig = go.Figure()

    for estado in estados:
        for vacuna in tipos_vacunas:
            if (vacuna == "Gripe"):
                fig.add_trace(
                go.Scatter(
                    x = (df_totales_por_vacuna['Semana']
                         [df_totales_por_vacuna["Estado"] == estado]
                         [df_totales_por_vacuna['Vacuna'] == vacuna]),
                    y = (df_totales_por_vacuna['Cantidad']
                        [df_totales_por_vacuna["Estado"] == estado]
                        [df_totales_por_vacuna['Vacuna'] == vacuna]),
                    name = estado, visible = True
                )
            )
            else:
                fig.add_trace(
                go.Scatter(
                    x = (df_totales_por_vacuna['Semana']
                        [df_totales_por_vacuna["Estado"] == estado]
                        [df_totales_por_vacuna['Vacuna'] == vacuna]),
                    y = (df_totales_por_vacuna['Cantidad']
                        [df_totales_por_vacuna["Estado"] == estado]
                        [df_totales_por_vacuna['Vacuna'] == vacuna]),
                    name = estado, visible = False
                )
            )

    buttons = []

    for i, tipo in enumerate(tipos_vacunas):
        args = [False] * len(tipos_vacunas)
        args[i] = True

        button = dict(label = tipo,
                      method = "update",
                      args = [{"visible": args}])

        buttons.append(button)

    fig.update_layout(
        updatemenus = [dict(
                        active=  0,
                        type = "dropdown",
                        buttons = buttons,
                        x = 0,
                        y = 1.1,
                        xanchor = 'left',
                        yanchor = 'bottom'
                    )], 
        autosize = False,
        width = 1000,
       height = 800,
       yaxis = dict(range = [-1, 9]) 
    )

    context['grafico_vacuna'] = fig.to_html()

    df_total = df_vacunas.groupby(["Estado"]).sum().reset_index()
    fig = px.pie(df_total, values = "Cantidad", names = 'Estado', 
        title = 'Porcentaje total segun estado')

    #AGREGAR RANGE_SELECTORS

    context["grafico_total"] = fig.to_html()
    print(context["mensaje"])
    return render(request, "visualizacion_estadisticas.html", context)

@login_required
def ver_perfil(request):
    user = request.user
    if (user.rol_actual != "Ciudadano"):
        return redirigir_por_rol(request)
    context = request.session.get("context", {})
    request.session["context"] = {}


    if (context == {}):
        context["mensaje"] = ""
    context["DNI"] = user.dni
    context["nombre_apellido"] = user.nombre_apellido
    context["fecha_nacimiento"] = user.fecha_nacimiento
    context["mail"] = user.email
    context["cuestionario"] = user.de_riesgo
    context["vacunatorio_pref"] = user.vacunatorio_pref.nombre
    print(context["vacunatorio_pref"])
    vacunatorio = Vacunatorio
    context["vacunatorios"] = vacunatorio.objects.filter()
 


    return render(request, "perfil.html", context) 