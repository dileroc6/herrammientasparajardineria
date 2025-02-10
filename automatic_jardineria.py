import requests
import openai
from bs4 import BeautifulSoup
import os

# Configuración de WordPress
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WP_USER")
WP_PASSWORD = os.getenv("WP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extraer_articulo(url):
    """ Extrae el contenido del artículo original. """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    titulo = soup.find("h1").text if soup.find("h1") else "Artículo sin título"
    contenido = " ".join([p.text for p in soup.find_all("p")])

    imagen_tag = soup.find("img")
    imagen = imagen_tag["src"] if imagen_tag and "src" in imagen_tag.attrs else None

    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

def generar_contenido(titulo, contenido):
    """ Usa ChatGPT para generar un artículo único y optimizado. """
    openai.api_key = OPENAI_API_KEY
    prompt = f"Escribe un artículo SEO optimizado sobre: {titulo}. Usa información valiosa basada en este contenido: {contenido}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

def subir_imagen_wp(imagen_url):
    """ Sube la imagen a WordPress y devuelve su ID. """
    img_data = requests.get(imagen_url).content
    headers = {"Authorization": f"Basic {WP_USER}:{WP_PASSWORD}"}
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
                             headers=headers,
                             files={"file": ("imagen.jpg", img_data, "image/jpeg")})
    return response.json().get("id")

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """ Publica el artículo en WordPress. """
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