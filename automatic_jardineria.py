import re

def limpiar_y_formatear_contenido(contenido):
    """Convierte Markdown en HTML correctamente, asegurando formato adecuado y capitalización correcta en títulos."""
    
    # Extraer el título H1 si existe y asegurarse de que solo tenga mayúscula en la primera letra
    match_h1 = re.match(r'^\s*#\s*(.+)', contenido)
    if match_h1:
        titulo_h1 = f"<h1>{match_h1.group(1).capitalize()}</h1>"
        contenido = re.sub(r'^\s*#\s*.+\n', '', contenido, count=1)  # Eliminar H1 del contenido
    else:
        titulo_h1 = ""

    # Convertir encabezados Markdown a HTML asegurando mayúscula solo en la primera letra
    def formatear_encabezados(match):
        nivel = len(match.group(1))  # Longitud de los #
        texto = match.group(2).capitalize()  # Primera letra en mayúscula
        return f"<h{nivel}>{texto}</h{nivel}>"

    contenido = re.sub(r'^\s*(#{2,6})\s*(.*?)\s*$', formatear_encabezados, contenido, flags=re.MULTILINE)

    # Convertir **negritas** en <strong>
    contenido = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', contenido)

    # Convertir saltos de línea dobles en párrafos
    contenido = re.sub(r'\n\n+', '</p><p>', contenido)
    contenido = f"<p>{contenido}</p>"  # Envuelve todo en <p>

    # Formatear enlaces de [Texto](URL) a <a href="URL">Texto</a>
    contenido = re.sub(r'\[(.*?)\]\((https?://.*?)\)', r'<a href="\2">\1</a>', contenido)

    # Retornar el título H1 separado del contenido
    return titulo_h1 + contenido