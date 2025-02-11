import requests
import openai
from bs4 import BeautifulSoup
import os
import base64
import re

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

log("🚀 Inicio del proceso de publicación en WordPress.")

def get_auth_headers():
    """Devuelve los encabezados de autenticación correctos para WordPress."""
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }

def extraer_articulo(url):
    """ Extrae el contenido del artículo original. """
    log(f"🔍 Extrayendo artículo de: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    titulo = soup.find("h1").text.strip() if soup.find("h1") else "Artículo sin título"
    titulo = limpiar_y_formatear_titulo(titulo)
    contenido = " ".join([p.text for p in soup.find_all("p")])
    imagen_tag = soup.find("img")
    imagen = imagen_tag["src"] if imagen_tag and "src" in imagen_tag.attrs else None

    log(f"✅ Título original: {titulo}")
    log(f"📝 Contenido extraído: {contenido[:100]}...")  # Solo muestra los primeros 100 caracteres
    log(f"🖼️ Imagen encontrada: {imagen}")

    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

def limpiar_y_formatear_titulo(titulo):
    """ Elimina los prefijos como 'H1:', 'H2:' y capitaliza correctamente el título. """
    titulo_limpio = re.sub(r'^(H\d+:)\s*', '', titulo).strip()
    return titulo_limpio.capitalize()

def limpiar_y_formatear_contenido(contenido):
    """Convierte Markdown en HTML correctamente."""
    
    # Convertir encabezados de Markdown en HTML correctamente
    contenido = re.sub(r'^\s*(#{1,6})\s*(.*?)\s*$', 
                       lambda m: f"<h{len(m.group(1))}>{m.group(2)}</h{len(m.group(1))}>", 
                       contenido, 
                       flags=re.MULTILINE)

    # Convertir **negritas** en <strong>negritas</strong>
    contenido = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', contenido)

    # Convertir saltos de línea dobles en párrafos
    contenido = re.sub(r'\n\n+', '</p><p>', contenido)  # Divide en párrafos correctamente
    contenido = f"<p>{contenido}</p>"  # Envuelve todo en <p> inicial y final

    # Formatear enlaces en formato [Texto](URL) a <a href="URL">Texto</a>
    contenido = re.sub(r'\[(.*?)\]\((https?://.*?)\)', r'<a href="\2">\1</a>', contenido)

    return contenido

def generar_contenido(titulo, contenido):
    """ Usa ChatGPT para generar un artículo único y optimizado. """
    log(f"🤖 Generando contenido para: {titulo}")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
    Genera un artículo original y optimizado para SEO sobre "{titulo}", utilizando únicamente la información proporcionada en el contenido de referencia.

    Requisitos:
    - Usa solo la información del contenido original, sin agregar datos externos.
    - Estructura el texto con encabezados jerárquicos (H1, H2, H3) para mejorar la legibilidad y el SEO.
    - Aplica técnicas de optimización SEO, incluyendo el uso natural de palabras clave relevantes.
    - Utiliza listas, negritas y enlaces internos para mejorar la experiencia del usuario.
    - Finaliza el artículo con un comentario propio que aporte valor adicional sobre el tema.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en redacción de artículos SEO."},
            {"role": "user", "content": prompt}
        ]
    )

    resultado = response.choices[0].message.content.strip()

    # Separar el título del contenido
    lineas = resultado.split("\n")
    nuevo_titulo = lineas[0].strip()  # Primera línea como título
    nuevo_contenido = "\n".join(lineas[1:]).strip()  # Resto como contenido

    # Aplicar formato HTML correcto
    nuevo_contenido = limpiar_y_formatear_contenido(nuevo_contenido)

    # Limpiar y formatear el título generado
    nuevo_titulo = limpiar_y_formatear_titulo(nuevo_titulo)

    # Validar si la primera línea es un título correcto
    if len(nuevo_titulo) < 10 or not any(c.isalpha() for c in nuevo_titulo):  
        log("⚠️ El título generado no es válido, usando el original.")  
        nuevo_titulo = limpiar_y_formatear_titulo(titulo)  
        
    log(f"🎯 Título final a publicar: {nuevo_titulo}")
    log(f"📝 Contenido generado: {nuevo_contenido[:100]}...")  # Muestra los primeros 100 caracteres

    return nuevo_titulo, nuevo_contenido

def subir_imagen_a_wordpress(img_url):
    """ Descarga y sube una imagen a WordPress, devolviendo su ID. """
    if not img_url:
        log("⚠️ No se encontró imagen para subir.")
        return None

    log(f"📸 Descargando imagen desde: {img_url}")
    img_response = requests.get(img_url)
    if img_response.status_code != 200:
        log(f"❌ Error al descargar la imagen: {img_response.status_code}")
        return None

    log("📸 Subiendo imagen a WordPress...")
    headers = get_auth_headers()

    files = {
        "file": ("imagen.jpg", img_response.content, "image/jpeg")
    }
    
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, files=files)

    log(f"📸 Respuesta de WordPress: {response.status_code} - {response.text}")
    if response.status_code == 201:
        return response.json().get("id")
    else:
        log(f"❌ Error al subir la imagen: {response.text}")
        return None

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
    log(f"🚀 Publicando en WordPress: {titulo}")

    headers = get_auth_headers()
    data = {
        "title": titulo,
        "content": contenido,
        "status": "publish",
        "categories": [17],  # ID de la categoría 'cortasetos'
    }
    if imagen_id:
        data["featured_media"] = imagen_id

    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=data, headers=headers)
    
    log(f"📢 Respuesta de WordPress: {response.status_code} - {response.text}")
    return response.json()

# Leer URLs desde lista_enlaces.txt
with open("lista_enlaces.txt", "r") as file:
    urls = [line.strip() for line in file.readlines() if line.strip()]

for url in urls:
    datos = extraer_articulo(url)
    if datos:
        nuevo_titulo, nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
        imagen_id = subir_imagen_a_wordpress(datos["imagen"]) if datos["imagen"] else None
        publicar_en_wordpress(nuevo_titulo, nuevo_contenido, imagen_id)

log("✅ Publicación finalizada.")