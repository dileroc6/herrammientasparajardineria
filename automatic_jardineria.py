def generar_contenido(titulo, contenido):
    """Genera un artículo sin repetir el título en el contenido."""
    log(f"🤖 Generando contenido para: {titulo}")

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""
        Genera un artículo optimizado para SEO sobre "{titulo}" usando la información proporcionada.
        - NO incluyas el título en el contenido, solo usa encabezados H2 en adelante.
        - Aplica técnicas SEO y palabras clave relevantes.
        - Usa listas, negritas y enlaces internos.
        - Concluye con un comentario propio de valor adicional.
        """

        log("📡 Enviando solicitud a OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en redacción de artículos SEO."},
                {"role": "user", "content": prompt}
            ]
        )
        log("✅ Respuesta recibida de OpenAI.")

        resultado = response.choices[0].message.content.strip()
        log(f"📜 Contenido generado: {resultado[:100]}...")  

        nuevo_contenido = limpiar_y_formatear_contenido(resultado)  # Limpieza final

        log(f"📝 Título final: {titulo}")
        return titulo, nuevo_contenido  # No agregamos <h1> aquí

    except Exception as e:
        log(f"❌ Error al generar contenido: {str(e)}")
        return titulo, contenido  # Devuelve el contenido original si hay error