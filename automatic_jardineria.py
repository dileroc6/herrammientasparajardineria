import requests
import openai
from bs4 import BeautifulSoup
import os

# Archivo de log
LOG_FILE = "log.txt"

def log(mensaje):
    """Guarda el mensaje en el archivo de log y lo imprime en consola."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")
    print(mensaje)

# Configuración del WordPress
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WP_USER")
WP_PASSWORD = os.getenv("WP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

log("🚀 Inicio del proceso de publicación en WordPress.")

def extraer_articulo(url):
    """ Extrae el contenido del artículo original. """
    log(f"🔍 Extrayendo artículo de: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    titulo = soup.find("h1").text if soup.find("h1") else "Artículo sin título"
    contenido = " ".join([p.text for p in soup.find_all("p")])
    imagen_tag = soup.find("img")
    imagen = imagen_tag["src"] if imagen_tag and "src" in imagen_tag.attrs else None

    log(f"✅ Título: {titulo}")
    log(f"📝 Contenido extraído: {contenido[:100]}...")  # Solo muestra los primeros 100 caracteres
    log(f"🖼️ Imagen encontrada: {imagen}")

    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

def generar_contenido(titulo, contenido):
    """ Usa ChatGPT para generar un artículo único y optimizado. """
    log(f"🤖 Generando contenido para: {titulo}")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"Escribe un artículo SEO optimizado sobre: {titulo}. Usa información valiosa basada en este contenido: {contenido}"
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
                {"role": "system", "content": "Eres un asistente experto en redacción de artículos SEO y conocedor de todo lo relacionado con perros."},
                {"role": "user", "content": prompt}
        ]
    )

    resultado = response.choices[0].message.content
    log(f"📝 Contenido generado: {resultado[:100]}...")  # Solo muestra los primeros 100 caracteres

    return resultado

def subir_imagen_wp(imagen_url):
    """ Sube la imagen a WordPress y devuelve su ID. """
    log(f"📤 Subiendo imagen: {imagen_url}")

    img_data = requests.get(imagen_url).content
    headers = {"Authorization": f"Basic {WP_USER}:{WP_PASSWORD}"}
    
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
                             headers=headers,
                             files={"file": ("imagen.jpg", img_data, "image/jpeg")})

    log(f"📸 Respuesta de WordPress: {response.status_code} - {response.text}")
    return response.json().get("id")

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
    log(f"🚀 Publicando en WordPress: {titulo}")

    headers = {
        "Authorization": f"Basic {WP_USER}:{WP_PASSWORD}",
        "Content-Type": "application/json"
    }
    data = {
        "title": titulo,
        "content": contenido,
        "status": "publish",
        "categories": [123],  # ID de la categoría 'cortasetos'
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
        nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
        imagen_id = subir_imagen_wp(datos["imagen"]) if datos["imagen"] else None
        publicar_en_wordpress(datos["titulo"], nuevo_contenido, imagen_id)

log("✅ Publicación finalizada.")