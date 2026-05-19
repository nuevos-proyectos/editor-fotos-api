import os
import urllib.request
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import json

app = Flask(__name__)

FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
FONT_PATH = "Roboto-Regular.ttf"
if not os.path.exists(FONT_PATH):
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)

def wrap_text(text, font, max_width):
    """Divide el texto en líneas para que quepan en el ancho definido."""
    lines = []
    for line in text.split('\n'):
        if not line.strip():
            lines.append('')
            continue
        
        words = line.split(' ')
        current_line = []
        for word in words:
            if current_line:
                test_line = ' '.join(current_line + [word])
            else:
                test_line = word
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w < max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
    return "\n".join(lines)

def parsear_texto(texto_raw):
    """Parsea el JSON o string y lo formatea para mostrar"""
    try:
        if isinstance(texto_raw, str):
            datos = json.loads(texto_raw)
        else:
            datos = texto_raw
        
        lineas = []
        
        if 'observaciones' in datos:
            observaciones = datos['observaciones']
            if isinstance(observaciones, list):
                for obs in observaciones:
                    if isinstance(obs, dict):
                        for key, value in obs.items():
                            lineas.append(f"{key}: {value}")
                    else:
                        lineas.append(str(obs))
            else:
                lineas.append(f"Observaciones: {observaciones}")
        else:
            for key, value in datos.items():
                if key not in ['NoteCam']:
                    lineas.append(f"{key}: {value}")
        
        if 'NoteCam' in datos:
            lineas.append(f"NoteCam: {datos['NoteCam']}")
            
        return "\n".join(lineas)
    except:
        return texto_raw

@app.route('/editar', methods=['POST'])
def editar_foto():
    if 'foto' not in request.files:
        return "Falta la foto", 400
    
    file = request.files['foto']
    texto_raw = request.form.get('texto', 'Sin datos')

    # Abrir imagen
    img = Image.open(file.stream).convert("RGBA")
    ancho, alto = img.size

    # Parsear y formatear el texto
    texto_formateado = parsear_texto(texto_raw)
    
    print(f"Texto formateado:\n{texto_formateado}")

    # --- CONFIGURACIÓN DEL RECUADRO - ANCHO 25% ---
    ancho_recuadro = int(ancho * 0.25)  # 25% del ancho de la imagen
    padding = 15  # Padding más pequeño porque el recuadro es angosto
    ancho_texto_disponible = ancho_recuadro - (padding * 2)

    # Fuentes más pequeñas para que quepan en el recuadro angosto
    try:
        fuente_titulo = ImageFont.truetype(FONT_PATH, 18)
        fuente_texto = ImageFont.truetype(FONT_PATH, 14)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()

    # Ajustar el texto al ancho del recuadro
    lineas_originales = texto_formateado.split('\n')
    lineas_ajustadas = []
    
    for linea in lineas_originales:
        if linea.startswith('Latitud:') or linea.startswith('Longitud:') or linea.startswith('Nota:'):
            # Usar fuente más pequeña para estos campos
            linea_ajustada = wrap_text(linea, fuente_texto, ancho_texto_disponible)
        else:
            linea_ajustada = wrap_text(linea, fuente_texto, ancho_texto_disponible)
        
        if '\n' in linea_ajustada:
            lineas_ajustadas.extend(linea_ajustada.split('\n'))
        else:
            lineas_ajustadas.append(linea_ajustada)
    
    texto_final = '\n'.join(lineas_ajustadas)
    
    # Calcular altura necesaria
    lineas_finales = texto_final.split('\n')
    alto_total_texto = 0
    
    for i, linea in enumerate(lineas_finales):
        if i == 0:
            bbox = fuente_titulo.getbbox(linea)
            alto_total_texto += (bbox[3] - bbox[1]) + 5
        else:
            if linea.strip():
                bbox = fuente_texto.getbbox(linea)
                alto_total_texto += (bbox[3] - bbox[1]) + 4
    
    alto_recuadro = alto_total_texto + (padding * 2)

    # Posición - INFERIOR IZQUIERDA
    margen = 20
    x1 = margen
    y1 = alto - alto_recuadro - margen
    x2 = x1 + ancho_recuadro
    y2 = alto - margen

    # Crear capa para el recuadro
    capa_recuadro = Image.new('RGBA', img.size, (255, 255, 255, 0))
    dibujo = ImageDraw.Draw(capa_recuadro)
    
    # Dibujar recuadro semitransparente
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(0, 0, 0, 200))
    
    # Dibujar el texto línea por línea
    y_offset = y1 + padding
    
    for i, linea in enumerate(lineas_finales):
        if not linea.strip():
            y_offset += 10
            continue
            
        if i == 0:
            # Primera línea (título) en amarillo
            dibujo.text((x1 + padding, y_offset), linea, font=fuente_titulo, fill=(255, 255, 100, 255))
            bbox = fuente_titulo.getbbox(linea)
            y_offset += (bbox[3] - bbox[1]) + 8
        else:
            # Resto de líneas en blanco
            dibujo.text((x1 + padding, y_offset), linea, font=fuente_texto, fill=(255, 255, 255, 255))
            bbox = fuente_texto.getbbox(linea)
            y_offset += (bbox[3] - bbox[1]) + 5

    # Combinar imágenes
    imagen_final = Image.alpha_composite(img, capa_recuadro).convert("RGB")

    # Guardar en memoria
    img_io = io.BytesIO()
    imagen_final.save(img_io, 'JPEG', quality=90)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='foto_con_metadatos.jpg')

@app.route('/')
def index():
    return "API de edición de fotos - Usa POST a /editar con campo 'foto' y 'texto'"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
