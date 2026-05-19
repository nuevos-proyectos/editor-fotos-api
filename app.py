import os
import urllib.request
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

# MAGIA 1: Descargar una fuente profesional (Roboto) si el servidor no la tiene
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

    # MAGIA 2: Cargar la fuente grande (Tamaño 45)
    try:
        fuente = ImageFont.truetype(FONT_PATH, 45)
    except IOError:
        fuente = ImageFont.load_default()

    # MAGIA 3: Hacer el recuadro más grande para que quepan las letras grandes
    margen = 20
    ancho_recuadro = 700  # Más ancho
    alto_recuadro = 250   # Más alto
    x1 = margen
    y1 = alto - alto_recuadro - margen
    x2 = x1 + ancho_recuadro
    y2 = alto - margen

    # Dibujar fondo blanco semitransparente
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(255, 255, 255, 180))

    # Escribir usando la fuente nueva
    dibujo.text((x1 + 20, y1 + 20), texto_datos, font=fuente, fill=(0, 0, 0, 255))

    imagen_final = Image.alpha_composite(img, capa_recuadro).convert("RGB")

    img_io = io.BytesIO()
    imagen_final.save(img_io, 'JPEG', quality=85)
    img_io.seek(0)

    # MAGIA 4: Obligar a n8n a reconocer que es una imagen JPG
    return send_file(
        img_io, 
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='foto_cierre_obra.jpg'
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
