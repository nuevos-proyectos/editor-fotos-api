import os
import urllib.request
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
FONT_PATH = "Roboto-Regular.ttf"
if not os.path.exists(FONT_PATH):
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)

def wrap_text(text, font, max_width):
    """Divide el texto en líneas para que quepan en el ancho definido."""
    lines = []
    for line in text.split('\n'):
        words = line.split(' ')
        current_line = []
        for word in words:
            # Probar si la palabra cabe en la línea
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w < max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
    return "\n".join(lines)

@app.route('/editar', methods=['POST'])
def editar_foto():
    if 'foto' not in request.files:
        return "Falta la foto", 400
    
    file = request.files['foto']
    texto_raw = request.form.get('texto', 'Sin datos')

    img = Image.open(file.stream).convert("RGBA")
    ancho, alto = img.size

    # --- CONFIGURACIÓN DE ANCHO FIJO (80% de la imagen) ---
    ancho_recuadro = int(ancho * 0.8)
    padding = 40
    ancho_texto_disponible = ancho_recuadro - (padding * 2)

    try:
        fuente = ImageFont.truetype(FONT_PATH, 45)
    except IOError:
        fuente = ImageFont.load_default()

    # Ajustar el texto al ancho fijo
    texto_ajustado = wrap_text(texto_raw, fuente, ancho_texto_disponible)

    # Calcular altura basada en el texto ajustado
    dibujo_temp = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = dibujo_temp.multiline_textbbox((0, 0), texto_ajustado, font=fuente)
    alto_texto = bbox[3] - bbox[1]
    
    alto_recuadro = alto_texto + (padding * 2)

    # Posición - INFERIOR IZQUIERDA
    margen_pantalla = 40
    x1 = margen_pantalla  # <--- Cambiado: fijo a la izquierda
    y1 = alto - alto_recuadro - margen_pantalla
    x2 = x1 + ancho_recuadro
    y2 = alto - margen_pantalla

    # Dibujar
    capa_recuadro = Image.new('RGBA', img.size, (255,255,255,0))
    dibujo = ImageDraw.Draw(capa_recuadro)
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(255, 255, 255, 180))
    dibujo.multiline_text((x1 + padding, y1 + padding), texto_ajustado, font=fuente, fill=(0, 0, 0, 255))

    imagen_final = Image.alpha_composite(img, capa_recuadro).convert("RGB")

    img_io = io.BytesIO()
    imagen_final.save(img_io, 'JPEG', quality=85)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='foto_cierre_obra.jpg')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
