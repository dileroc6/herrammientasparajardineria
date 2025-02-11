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

    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

def limpiar_y_formatear_titulo(titulo):
    """ Elimina los prefijos como 'H1:', 'H2:' y capitaliza correctamente el título. """
    titulo_limpio = re.sub(r'^(H\d+:)\s*', '', titulo).strip()
    return titulo_limpio.capitalize()

def limpiar_y_formatear_contenido(contenido):
    """Convierte Markdown en HTML correctamente."""
    contenido = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', contenido)  # Negritas
    contenido = re.sub(r'\n\n+', '</p><p>', contenido)  # Párrafos
    contenido = f"<p>{contenido}</p>"
    contenido = re.sub(r'\[(.*?)\]\((https?://.*?)\)', r'<a href="\2">\1</a>', contenido)  # Enlaces
    return contenido

def generar_contenido(titulo, contenido):
    """ Usa ChatGPT para generar un artículo único y optimizado. """
    log(f"🤖 Generando contenido para: {titulo}")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
    Genera un artículo optimizado para SEO sobre "{titulo}" usando la información proporcionada.
    - Usa etiqutas html, encabezados jerárquicos (H1, H2, H3) (NO uses prefijos como "H1:", "H2:", etc.).
    - Aplica técnicas SEO y palabras clave relevantes.
    - Incluye listas, negritas y enlaces internos.
    - Concluye con un comentario propio de valor adicional.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en redacción de artículos SEO."},
            {"role": "user", "content": prompt}
        ]
    )

    resultado = response.choices[0].message.content.strip()
    nuevo_titulo = limpiar_y_formatear_titulo(resultado.split("\n")[0])
    nuevo_contenido = limpiar_y_formatear_contenido("\n".join(resultado.split("\n")[1:]))
    return nuevo_titulo, nuevo_contenido

def subir_imagen_a_wordpress(img_url):
    """ Descarga y sube una imagen a WordPress. """
    if not img_url:
        return None
    response = requests.get(img_url)
    if response.status_code != 200:
        return None
    headers = get_auth_headers()
    files = {"file": ("imagen.jpg", response.content, "image/jpeg")}
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, files=files)
    return response.json().get("id") if response.status_code == 201 else None

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
    headers = get_auth_headers()
    data = {"title": titulo, "content": contenido, "status": "publish"}
    if imagen_id:
        data["featured_media"] = imagen_id
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=data, headers=headers)
    return response.json()

with open("lista_enlaces.txt", "r") as file:
    urls = [line.strip() for line in file.readlines() if line.strip()]

for url in urls:
    datos = extraer_articulo(url)
    if datos:
        nuevo_titulo, nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
        imagen_id = subir_imagen_a_wordpress(datos["imagen"]) if datos["imagen"] else None
        publicar_en_wordpress(nuevo_titulo, nuevo_contenido, imagen_id)

log("✅ Publicación completada.")
