import requests
import openai
from bs4 import BeautifulSoup
import os
import base64
import re
import json

# Archivo de logs
LOG_FILE = "log.txt"

def log(mensaje):
    """Guarda el mensaje en el archivo de log y lo imprime en consola."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")
    print(mensaje)

# Configuración de WordPress y OpenAI
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WP_USER")
WP_PASSWORD = os.getenv("WP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_auth_headers():
    """Devuelve los encabezados de autenticación correctos para WordPress."""
    try:
        credentials = f"{WP_USER}:{WP_PASSWORD}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        log(f"⚠️ Error generando encabezados de autenticación: {e}")
        return {}

def extraer_articulo(url):
    """ Extrae el contenido del artículo original. """
    try:
        log(f"🔍 Extrayendo artículo de: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            log(f"⚠️ Error al obtener la página: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        titulo = soup.find("h1").text.strip() if soup.find("h1") else "Artículo sin título"
        titulo = limpiar_y_formatear_titulo(titulo)
        contenido = " ".join([p.text for p in soup.find_all("p")])
        imagen_tag = soup.find("img")
        imagen = imagen_tag["src"] if imagen_tag and "src" in imagen_tag.attrs else None

        return {"titulo": titulo, "contenido": contenido, "imagen": imagen}
    except Exception as e:
        log(f"⚠️ Error extrayendo artículo de {url}: {e}")
        return None

def generar_contenido(titulo, contenido):
    """ Usa ChatGPT para generar un artículo único y optimizado. """
    try:
        log(f"🤖 Generando contenido para: {titulo}")
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"Genera un artículo SEO optimizado sobre '{titulo}'."
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en redacción SEO."},
                {"role": "user", "content": prompt}
            ]
        )
        resultado = response.choices[0].message.content.strip()
        nuevo_titulo = limpiar_y_formatear_titulo(resultado.split("\n")[0])
        nuevo_contenido = limpiar_y_formatear_contenido("\n".join(resultado.split("\n")[1:]))
        return nuevo_titulo, nuevo_contenido
    except Exception as e:
        log(f"⚠️ Error generando contenido para {titulo}: {e}")
        return titulo, contenido

def subir_imagen_a_wordpress(img_url):
    """ Descarga y sube una imagen a WordPress. """
    try:
        if not img_url:
            return None
        
        response = requests.get(img_url)
        if response.status_code != 200:
            log(f"⚠️ Error descargando imagen: {response.status_code}")
            return None
        
        headers = get_auth_headers()
        files = {"file": ("imagen.jpg", response.content, "image/jpeg")}
        response = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, files=files)
        
        if response.status_code == 201:
            return response.json().get("id")
        else:
            log(f"⚠️ Error subiendo imagen a WordPress: {response.status_code}")
            return None
    except Exception as e:
        log(f"⚠️ Error en subir_imagen_a_wordpress: {e}")
        return None

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
    try:
        headers = get_auth_headers()
        data = {"title": titulo, "content": contenido, "status": "publish"}
        if imagen_id:
            data["featured_media"] = imagen_id
        
        response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=data, headers=headers)
        
        if response.status_code in [200, 201]:
            log(f"✅ Publicado con éxito: {titulo}")
        else:
            log(f"⚠️ Error al publicar en WordPress: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"⚠️ Error en publicar_en_wordpress: {e}")

with open("lista_enlaces.txt", "r") as file:
    urls = [line.strip() for line in file.readlines() if line.strip()]

for url in urls:
    datos = extraer_articulo(url)
    if datos:
        nuevo_titulo, nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
        imagen_id = subir_imagen_a_wordpress(datos["imagen"]) if datos["imagen"] else None
        publicar_en_wordpress(nuevo_titulo, nuevo_contenido, imagen_id)

log("✅ Publicación completada.")
