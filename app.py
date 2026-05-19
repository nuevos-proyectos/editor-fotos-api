import os
import urllib.request
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

# Descargar fuente Roboto
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
FONT_PATH = "Roboto-Regular.ttf"
if not os.path.exists(FONT_PATH):
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)

@app.route('/editar', methods=['POST'])
def editar_foto():
    if 'foto' not in request.files:
        return "Falta la foto", 400
    
    file = request.files['foto']
    texto_datos = request.form.get('texto', 'Sin datos')

    img = Image.open(file.stream).convert("RGBA")
    ancho, alto = img.size

    capa_recuadro = Image.new('RGBA', img.size, (255,255,255,0))
    dibujo = ImageDraw.Draw(capa_recuadro)

    try:
        fuente = ImageFont.truetype(FONT_PATH, 45)
    except IOError:
        fuente = ImageFont.load_default()

    # --- MAGIA DINÁMICA ---
    # Calcular el tamaño exacto que ocupará el texto
    bbox = dibujo.multiline_textbbox((0, 0), texto_datos, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]

    margen_pantalla = 20
    padding_interno = 30  # Espacio entre el texto y el borde del recuadro

    # El tamaño del recuadro ahora se adapta al texto automáticamente
    ancho_recuadro = ancho_texto + (padding_interno * 2)
    alto_recuadro = alto_texto + (padding_interno * 2)

    x1 = margen_pantalla
    y1 = alto - alto_recuadro - margen_pantalla
    x2 = x1 + ancho_recuadro
    y2 = alto - margen_pantalla

    # Dibujar fondo blanco semitransparente
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(255, 255, 255, 180))

    # Escribir el texto respetando los márgenes internos
    dibujo.text((x1 + padding_interno, y1 + padding_interno), texto_datos, font=fuente, fill=(0, 0, 0, 255))

    imagen_final = Image.alpha_composite(img, capa_recuadro).convert("RGB")

    img_io = io.BytesIO()
    imagen_final.save(img_io, 'JPEG', quality=85)
    img_io.seek(0)

    return send_file(
        img_io, 
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='foto_cierre_obra.jpg'
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
