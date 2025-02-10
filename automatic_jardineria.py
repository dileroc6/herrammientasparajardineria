import requests
import openai
import base64
from bs4 import BeautifulSoup
import json
import os

# Configuración de API Keys y credenciales
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WORDPRESS_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WP_USER")
WP_PASSWORD = os.getenv("WP_PASSWORD")

openai.api_key = OPENAI_API_KEY

# Función para extraer contenido del artículo original
def extraer_articulo(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error al obtener el artículo: {url}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    titulo = soup.find("h1").text.strip() if soup.find("h1") else ""
    contenido = "\n".join([p.text for p in soup.find_all("p")])
    imagen = soup.find("img")["src"] if soup.find("img") else None
    
    return {"titulo": titulo, "contenido": contenido, "imagen": imagen}

# Función para generar un artículo único con ChatGPT
def generar_contenido(titulo, contenido_original):
    prompt = f"""
    Escribe un artículo original optimizado para SEO basado en el tema: "{titulo}". 
    Debe ser único, con información valiosa, encabezados H2, listas y enlaces internos.
    No copies el contenido, reescríbelo de manera original y estructurada.
    
    Información de referencia: {contenido_original}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# Función para subir la imagen destacada a WordPress
def subir_imagen_wp(url_imagen):
    response = requests.get(url_imagen)
    if response.status_code == 200:
        img_data = response.content
        nombre_imagen = url_imagen.split("/")[-1]
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{WP_USER}:{WP_PASSWORD}'.encode()).decode()}",
            "Content-Disposition": f'attachment; filename="{nombre_imagen}"'
        }
        
        response = requests.post(f"{WORDPRESS_URL}/wp-json/wp/v2/media", headers=headers, files={"file": img_data})
        
        if response.status_code == 201:
            return response.json()["id"]  # Devuelve el ID de la imagen subida
    return None

# Función para publicar en WordPress
def publicar_en_wordpress(titulo, contenido, imagen_id):
    post_data = {
        "title": titulo,
        "content": contenido,
        "status": "publish",
        "categories": [123],  # ID de la categoría 'cortasetos'
        "featured_media": imagen_id
    }
    
    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{WP_USER}:{WP_PASSWORD}'.encode()).decode()}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{WORDPRESS_URL}/wp-json/wp/v2/posts", headers=headers, json=post_data)
    
    if response.status_code == 201:
        print(f"Publicado: {titulo}")
    else:
        print(f"Error al publicar: {response.text}")

# Leer lista de enlaces
def procesar_lista_enlaces(archivo):
    with open(archivo, "r") as f:
        enlaces = [line.strip() for line in f.readlines() if line.strip()]
    
    for enlace in enlaces:
        datos = extraer_articulo(enlace)
        if datos:
            nuevo_contenido = generar_contenido(datos["titulo"], datos["contenido"])
            imagen_id = subir_imagen_wp(datos["imagen"]) if datos["imagen"] else None
            publicar_en_wordpress(datos["titulo"], nuevo_contenido, imagen_id)

# Ejecutar el proceso
if __name__ == "__main__":
    procesar_lista_enlaces("lista_enlaces.txt")
