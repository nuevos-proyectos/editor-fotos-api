import os
import urllib.request
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import json
from io import BytesIO

app = Flask(__name__)

FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
FONT_PATH = "Roboto-Regular.ttf"
LOGO_URL = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhLvoXGdAuh0fCc7ijQ1dLoXj5JfSGsfg9121JALww3V_cZAi1S3bi2AlOfRi4OaL4QgA0Tg-L3vILiU2arsbL114YCYBSQxJdMQq-7mEmg2_NFdkkltiFPFP2WVn4v433B8Nqkt7FCA_o4X27GLmMNkEs2AqWanPc_4gZMAPOjE7FgI42yt3pjE6C24Io/s202/Picsart_26-01-01_23-01-18-178.png"

if not os.path.exists(FONT_PATH):
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)

def descargar_logo():
    """Descarga el logo desde la URL usando urllib"""
    try:
        with urllib.request.urlopen(LOGO_URL, timeout=10) as response:
            logo_data = response.read()
            logo = Image.open(BytesIO(logo_data))
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            return logo
    except Exception as e:
        print(f"Error descargando logo: {e}")
        return None

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

    # --- CONFIGURACIÓN DEL RECUADRO - ANCHO 28% ---
    ancho_recuadro = int(ancho * 0.28)
    padding = 15
    ancho_texto_disponible = ancho_recuadro - (padding * 2)

    # Fuentes
    try:
        fuente_titulo = ImageFont.truetype(FONT_PATH, 16)
        fuente_texto = ImageFont.truetype(FONT_PATH, 12)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()

    # Procesar el texto
    lineas_originales = texto_formateado.split('\n')
    lineas_ajustadas = []
    
    for linea in lineas_originales:
        linea_ajustada = wrap_text(linea, fuente_texto, ancho_texto_disponible)
        if '\n' in linea_ajustada:
            lineas_ajustadas.extend(linea_ajustada.split('\n'))
        else:
            lineas_ajustadas.append(linea_ajustada)
    
    # Descargar logo
    logo = descargar_logo()
    
    # Calcular alturas
    alto_texto_total = 0
    for linea in lineas_ajustadas:
        if linea.strip():
            bbox = fuente_texto.getbbox(linea)
            alto_texto_total += (bbox[3] - bbox[1]) + 4
    
    alto_logo = 0
    if logo:
        logo.thumbnail((ancho_recuadro - padding*2, 80), Image.Resampling.LANCZOS)
        alto_logo = logo.height + 10
    
    alto_recuadro = alto_texto_total + alto_logo + (padding * 2) + 10

    # Posición - INFERIOR IZQUIERDA
    margen = 20
    x1 = margen
    y1 = alto - alto_recuadro - margen
    x2 = x1 + ancho_recuadro
    y2 = alto - margen

    # Crear capa para el recuadro
    capa_recuadro = Image.new('RGBA', img.size, (255, 255, 255, 0))
    dibujo = ImageDraw.Draw(capa_recuadro)
    
    # Dibujar recuadro
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(0, 0, 0, 200))
    
    # Dibujar texto
    y_offset = y1 + padding
    
    for linea in lineas_ajustadas:
        if not linea.strip():
            y_offset += 8
            continue
        
        if linea.startswith('BOX:') or linea.startswith('Implementador:'):
            dibujo.text((x1 + padding, y_offset), linea, font=fuente_texto, fill=(255, 255, 100, 255))
        else:
            dibujo.text((x1 + padding, y_offset), linea, font=fuente_texto, fill=(255, 255, 255, 255))
        
        bbox = fuente_texto.getbbox(linea)
        y_offset += (bbox[3] - bbox[1]) + 4
    
    # Dibujar logo
    if logo:
        logo_x = x1 + padding
        logo_y = y2 - padding - logo.height
        capa_recuadro.paste(logo, (logo_x, logo_y), logo)

    # Combinar imágenes
    imagen_final = Image.alpha_composite(img, capa_recuadro).convert("RGB")

    # Guardar resultado
    img_io = io.BytesIO()
    imagen_final.save(img_io, 'JPEG', quality=90)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='foto_con_metadatos.jpg')

@app.route('/')
def index():
    return "API de edición de fotos - Usa POST a /editar"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
