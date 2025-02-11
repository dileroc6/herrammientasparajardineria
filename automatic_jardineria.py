import requests
import openai
from bs4 import BeautifulSoup
import os
import base64

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

    titulo = soup.find("h1").text if soup.find("h1") else "Artículo sin título"
    contenido = " ".join([p.text for p in soup.find_all("p")])
    imagen_tag = soup.find("img")
    imagen = imagen_tag["src"] if imagen_tag and "src" in imagen_tag.attrs else None

    log(f"✅ Título original: {titulo}")
    log(f"📝 Contenido extraído: {contenido[:100]}...")
    log(f"🖼️ Imagen encontrada: {imagen}")

    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

def limpiar_y_formatear_titulo(titulo):
    """ Limpia el título y lo capitaliza correctamente. """
    return titulo.replace("Título:", "").strip().capitalize()

def generar_contenido(titulo, contenido):
    """ Usa OpenAI para generar un artículo optimizado. """
    log(f"🤖 Generando contenido para: {titulo}")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"Genera un artículo SEO sobre {titulo} basado en {contenido} con encabezados y optimización."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en SEO."},
            {"role": "user", "content": prompt}
        ]
    )
    
    resultado = response.choices[0].message.content.strip()
    lineas = resultado.split("\n")
    nuevo_titulo = limpiar_y_formatear_titulo(lineas[0])
    nuevo_contenido = "\n".join(lineas[1:]).strip()

    if len(nuevo_titulo) < 10:
        log("⚠️ Título inválido, usando el original.")
        nuevo_titulo = limpiar_y_formatear_titulo(titulo)
    
    log(f"🎯 Título final: {nuevo_titulo}")
    return nuevo_titulo, nuevo_contenido

def subir_imagen_a_wordpress(img_url):
    """ Sube una imagen a WordPress y devuelve su ID. """
    if not img_url:
        log("⚠️ No se encontró imagen para subir.")
        return None
    
    log(f"📸 Descargando imagen: {img_url}")
    img_response = requests.get(img_url)
    if img_response.status_code != 200:
        log(f"❌ Error al descargar imagen: {img_response.status_code}")
        return None
    
    log("📸 Subiendo imagen a WordPress...")
    headers = get_auth_headers()
    files = {"file": ("imagen.jpg", img_response.content, "image/jpeg")}
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, files=files)
    
    if response.status_code == 201:
        return response.json().get("id")
    else:
        log(f"❌ Error al subir imagen: {response.text}")
        return None

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
    log(f"🚀 Publicando: {titulo}")
    headers = get_auth_headers()
    data = {"title": titulo, "content": contenido, "status": "publish", "categories": [17]}
    if imagen_id:
        data["featured_media"] = imagen_id
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=data, headers=headers)
    log(f"📢 Respuesta de WordPress: {response.status_code}")
    return response.json()

# Procesar URLs desde lista_enlaces.txt
with open("lista_enlaces.txt", "r") as file:
    urls = [line.strip() for line in file.readlines() if line.strip()]

for url in urls:
    datos = extraer_articulo(url)
    if datos:
        nuevo_titulo, nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
        imagen_id = subir_imagen_a_wordpress(datos["imagen"]) if datos["imagen"] else None
        publicar_en_wordpress(nuevo_titulo, nuevo_contenido, imagen_id)

log("✅ Publicación finalizada.")