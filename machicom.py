import asyncio
import requests
from telethon import TelegramClient, events
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os

# Configuración del cliente de Telegram
API_ID = '20451779'
API_HASH = 'da79d8408831a094d64edb184f253bab'
PHONE_NUMBER = '+51903356436'

# Inicializar cliente de Telegram
client = TelegramClient('mi_sesion_token', API_ID, API_HASH)

# Usuario administrador
ADMIN_USER = 'Asteriscom'

# Archivos JSON para almacenar permisos y URLs
ARCHIVO_PERMISOS = 'memoria_permisos.json'
ARCHIVO_URLS = 'memoria_urls.json'

# Diccionario para almacenar permisos con fecha de expiración
permisos = {}

# Lista de URLs asociadas a cada comando
URLS = {}

# Cargar permisos y URLs desde los archivos JSON
def cargar_permisos():
    if os.path.exists(ARCHIVO_PERMISOS):
        with open(ARCHIVO_PERMISOS, 'r') as archivo:
            datos = json.load(archivo)
            for usuario, tiempo in datos.items():
                permisos[usuario] = datetime.fromisoformat(tiempo)
    else:
        guardar_permisos()

def cargar_urls():
    if os.path.exists(ARCHIVO_URLS):
        with open(ARCHIVO_URLS, 'r') as archivo:
            datos = json.load(archivo)
            URLS.update(datos)
    else:
        guardar_urls()

# Guardar permisos y URLs en los archivos JSON
def guardar_permisos():
    datos = {usuario: tiempo.isoformat() for usuario, tiempo in permisos.items()}
    with open(ARCHIVO_PERMISOS, 'w') as archivo:
        json.dump(datos, archivo)

def guardar_urls():
    with open(ARCHIVO_URLS, 'w') as archivo:
        json.dump(URLS, archivo)

# Función para obtener datos de las URLs
async def obtener_datos(url):
    """Extrae el usuario, contraseña y token del HTML de la URL proporcionada."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            usuario = soup.find('label', text='Usuario:').find_next('input')['value']
            password = soup.find('label', text='Contraseña:').find_next('input')['value']
            token = soup.find('label', text='Token:').find_next('input')['value']

            return usuario, password, token
        else:
            return None, None, None
    except Exception as e:
        print(f"Error al obtener los datos de la URL {url}: {str(e)}")
        return None, None, None

async def manejar_comando(event, url):
    """Maneja la respuesta para cualquier comando registrado en la lista URLS."""
    sender = await event.get_sender()
    username = sender.username

    # Verificar si el usuario tiene permisos y si no ha expirado
    if username in permisos:
        if permisos[username] > datetime.now():
            usuario, password, token = await obtener_datos(url)

            if usuario and password and token:
                try:
                    await event.respond(usuario)
                    await event.respond(password)
                    await event.respond(token)
                except Exception as e:
                    print(f"Error al enviar mensaje a {username}: {str(e)}")
            else:
                await event.reply("❌ Error al obtener los datos del token.")
        else:
            await event.reply("❌ Tu membresía ha caducado contactate con @Asteriscom.")
    else:
        await event.reply("❌ No estás autorizado para usar este comando.")

# Comandos para otorgar permisos temporales
@client.on(events.NewMessage(pattern='/vip(\d+) (.+)'))
async def otorgar_permisos(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        dias = int(event.pattern_match.group(1))
        nuevo_usuario = event.pattern_match.group(2).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
        permisos[nuevo_usuario] = datetime.now() + timedelta(days=dias)
        
        # Guardar los permisos actualizados en JSON
        guardar_permisos()
        
        # Enviar confirmación al administrador y al usuario específico
        try:
            entity = await client.get_input_entity(nuevo_usuario)
            await event.reply(f"🎉 ¡Felicidades @{nuevo_usuario}, ahora cuentas con privilegios para poder consultar por {dias} días!")
            await client.send_message(entity, f"🎉 ¡Hola @{nuevo_usuario}, has recibido membresía VIP para consultar durante {dias} días!")
        except Exception as e:
            print(f"Error al enviar mensaje a {nuevo_usuario}: {str(e)}")
    else:
        await event.reply("❌ No tienes permiso para otorgar privilegios.")

# Comandos para quitar permisos temporales
@client.on(events.NewMessage(pattern='/uvip(\d+) (.+)'))
async def quitar_permisos(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        dias = int(event.pattern_match.group(1))
        usuario_a_quitar = event.pattern_match.group(2).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
        
        if usuario_a_quitar in permisos:
            permisos[usuario_a_quitar] -= timedelta(days=dias)
            
            # Guardar los permisos actualizados en JSON
            guardar_permisos()
            
            # Enviar confirmación al administrador y notificación al usuario específico
            try:
                entity = await client.get_input_entity(usuario_a_quitar)
                await event.reply(f"🕒 Se han restado {dias} días de la membresía de {usuario_a_quitar}.")
                await client.send_message(entity, f"🕒 Tu membresía ha sido reducida en {dias} días. Contacta con {ADMIN_USER} si tienes dudas.")
            except Exception as e:
                print(f"Error al enviar mensaje a {usuario_a_quitar}: {str(e)}")
        else:
            await event.reply(f"❌ No se encontraron permisos para {usuario_a_quitar}.")
    else:
        await event.reply("❌ No tienes permiso para modificar privilegios.")

# Comando para verificar tiempo restante de membresía
@client.on(events.NewMessage(pattern='/me (.+)'))
async def verificar_membresia(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    usuario_a_verificar = event.pattern_match.group(1).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
    
    if usuario_a_verificar in permisos:
        tiempo_restante = permisos[usuario_a_verificar] - datetime.now()
        dias, segundos = tiempo_restante.days, tiempo_restante.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        await event.reply(f"@{usuario_a_verificar} cuenta con {dias} días, {horas} horas y {minutos} minutos de membresía.")
    else:
        await event.reply(f"❌ No se encontraron permisos para {usuario_a_verificar}.")

# Comando para actualizar URLs
@client.on(events.NewMessage(pattern='/actualizar (\w+) (.+)'))
async def actualizar_url(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        comando = event.pattern_match.group(1)
        nueva_url = event.pattern_match.group(2)
        
        if comando in URLS:
            URLS[comando] = nueva_url
            # Guardar las URLs actualizadas en JSON
            guardar_urls()
            await event.reply(f"🔄 La URL para el comando /{comando} ha sido actualizada correctamente.")
        else:
            await event.reply(f"❌ El comando /{comando} no existe.")
    else:
        await event.reply("❌ No tienes permiso para actualizar URLs.")

# Comando para agregar nuevas URLs
@client.on(events.NewMessage(pattern='/agregar (\w+) (.+)'))
async def agregar_url(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        comando = event.pattern_match.group(1)
        nueva_url = event.pattern_match.group(2)
        
        if comando not in URLS:
            URLS[comando] = nueva_url
            # Guardar las URLs actualizadas en JSON
            guardar_urls()
            await event.reply(f"✅ El comando /{comando} ha sido agregado con la URL proporcionada.")
        else:
            await event.reply(f"❌ El comando /{comando} ya existe. Usa /actualizar para cambiar la URL.")
    else:
        await event.reply("❌ No tienes permiso para agregar nuevas URLs.")

# Comando para eliminar URLs
@client.on(events.NewMessage(pattern='/eliminar (\w+)'))
async def eliminar_url(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        comando = event.pattern_match.group(1)
        
        if comando in URLS:
            del URLS[comando]
            # Guardar las URLs actualizadas en JSON
            guardar_urls()
            await event.reply(f"🗑️ El comando /{comando} ha sido eliminado correctamente.")
        else:
            await event.reply(f"❌ El comando /{comando} no existe.")
    else:
        await event.reply("❌ No tienes permiso para eliminar URLs.")

# Comando para listar todos los comandos registrados (solo para el administrador)
@client.on(events.NewMessage(pattern='/cmds'))
async def listar_cmds(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        lista_comandos = [f"/{comando}: {url}" for comando, url in URLS.items()]
        if lista_comandos:
            await event.reply(f"📋 Lista de comandos registrados:\n" + "\n".join(lista_comandos))
        else:
            await event.reply("❌ No hay comandos registrados actualmente.")
    else:
        await event.reply("❌ No tienes permiso para ver los comandos registrados.")

# Comando para que los usuarios vean sus comandos disponibles
@client.on(events.NewMessage(pattern='/comandos'))
async def listar_comandos_usuario(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username in permisos:
        lista_comandos = [f"/{comando}" for comando, url in URLS.items()]
        if lista_comandos:
            await event.reply(f"📋 Lista de comandos disponibles para ti:\n" + "\n".join(lista_comandos))
        else:
            await event.reply("❌ No tienes comandos disponibles actualmente.")
    else:
        await event.reply("❌ No tienes una membresía activa para ver los comandos disponibles.")

# Registrar los comandos dinámicamente solo para usuarios con permisos
@client.on(events.NewMessage(pattern='/([a-zA-Z0-9_]+)'))
async def evento_handler(event):
    comando = event.pattern_match.group(1)
    if comando in URLS:
        url = URLS[comando]
        if event.is_private:
            await manejar_comando(event, url)

# Cargar permisos y URLs al iniciar el bot
cargar_permisos()
cargar_urls()

# Conexión persistente con reconexión automática en caso de error o caída de Internet
async def main():
    while True:
        try:
            await client.start(PHONE_NUMBER)
            print("Bot de token conectado y funcionando.")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Error detectado: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)  # Esperar unos segundos antes de intentar reconectar

# Iniciar el cliente de Telegram
with client:
    client.loop.run_until_complete(main())
