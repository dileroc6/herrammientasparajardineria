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
    """Convierte Markdown en HTML correctamente y ajusta títulos H2 y H3 para que solo la primera letra sea mayúscula."""
    contenido = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', contenido)  # Negritas
    contenido = re.sub(r'\n\n+', '</p><p>', contenido)  # Párrafos
    contenido = re.sub(r'\[(.*?)\]\((https?://.*?)\)', r'<a href="\2">\1</a>', contenido)  # Enlaces

    # Capitalizar solo la primera letra de títulos H1 H2 y H3
    contenido = re.sub(r'<(h1|h2|h3)>(.*?)</\1>', 
                       lambda match: f"<{match.group(1)}>{match.group(2).capitalize()}</{match.group(1)}>", 
                       contenido)

    return contenido

def generar_contenido(titulo, contenido):
    """Usa ChatGPT para generar un artículo único y optimizado con logs detallados."""
    log(f"🤖 Iniciando generación de contenido para: {titulo}")

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""
        Genera un artículo optimizado para SEO sobre "{titulo}" usando la información proporcionada.
        - La primera linea debe ser el titulo y despues de un salto de linea debe ir el contenido
        - Usa etiquetas HTML para todos los titulos H1, H2 y/o H3, etc.)
        - NO incluyas el título en el contenido
        - Los titulos h1, h2 y h3 deben iniciar con mayuscula y las demas letas deben ser minusculas
        - Aplica técnicas SEO y palabras clave relevantes.
        - Incluye listas, negritas y enlaces internos.
        - Incluye links a la fuente si es necesario.
        - Concluye con un comentario propio de valor adicional.
        - No menciones precios, enfocate en las características y beneficios.
        """

        log("📡 Enviando solicitud a OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en redacción de artículos SEO y en herramientas para jardinería."},
                {"role": "user", "content": prompt}
            ]
        )
        log("✅ Respuesta recibida de OpenAI.")

        resultado = response.choices[0].message.content.strip()
        log(f"📜 Contenido generado: {resultado[:100]}...")  # Muestra solo los primeros 100 caracteres para evitar logs largos

        # Extraer el título sin incluirlo en el contenido
        lineas = resultado.split("\n")
        nuevo_titulo = limpiar_y_formatear_titulo(lineas[0])  # Asume que la primera línea es el título
        nuevo_contenido = limpiar_y_formatear_contenido("\n".join(lineas[1:]))  # Resto del contenido sin el título

        log(f"📝 Título final: {nuevo_titulo}")
        return nuevo_titulo, nuevo_contenido

    except Exception as e:
        log(f"❌ Error al generar contenido: {str(e)}")
        return titulo, f"{titulo}\n{contenido}"  # Devuelve el contenido con un H1 si hay error
    
def subir_imagen_a_wordpress(url_imagen):
    """Descarga la imagen y la sube a WordPress como imagen destacada."""
    log(f"🖼️ Descargando imagen desde: {url_imagen}")

    try:
        respuesta = requests.get(url_imagen, stream=True)
        if respuesta.status_code != 200:
            log(f"❌ Error al descargar la imagen: {respuesta.status_code}")
            return None

        nombre_archivo = os.path.basename(url_imagen)
        headers = get_auth_headers()
        headers["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        headers["Content-Type"] = respuesta.headers["Content-Type"]

        log(f"📤 Subiendo imagen {nombre_archivo} a WordPress...")
        respuesta_wp = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=respuesta.content)

        if respuesta_wp.status_code == 201:
            imagen_id = respuesta_wp.json().get("id")
            log(f"✅ Imagen subida con éxito, ID: {imagen_id}")
            return imagen_id
        else:
            log(f"❌ Error al subir la imagen: {respuesta_wp.text}")
            return None

    except Exception as e:
        log(f"❌ Error en la subida de imagen: {str(e)}")
        return None

def publicar_en_wordpress(titulo, contenido, imagen_id=None):
    """Publica el artículo en WordPress con su título correcto y asignado a la categoría con ID 17."""
    log(f"🚀 Publicando en WordPress: {titulo}")

    headers = get_auth_headers()
    data = {
        "title": titulo,  # Asegurar que el título se usa correctamente
        "content": contenido,
        "status": "publish",
        "categories": [22]  # Asigna la entrada a la categoría con ID 17
    }
    if imagen_id:
        data["featured_media"] = imagen_id

    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=data, headers=headers)

    if response.status_code == 201:
        log(f"✅ Publicado con éxito: {titulo}")
    else:
        log(f"❌ Error al publicar: {response.text}")

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