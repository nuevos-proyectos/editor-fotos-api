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
    # Si el texto contiene saltos de línea, respetarlos
    for line in text.split('\n'):
        if not line.strip():
            lines.append('')
            continue
        
        words = line.split(' ')
        current_line = []
        for word in words:
            # Probar si la palabra cabe en la línea
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
        # Intentar parsear como JSON
        if isinstance(texto_raw, str):
            datos = json.loads(texto_raw)
        else:
            datos = texto_raw
        
        # Formatear los datos como texto legible
        lineas = []
        
        # Buscar observaciones o datos directamente
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
            # Si es un objeto plano, mostrar todos los campos
            for key, value in datos.items():
                if key not in ['NoteCam']:
                    lineas.append(f"{key}: {value}")
        
        # Agregar NoteCam si existe
        if 'NoteCam' in datos:
            lineas.append(f"NoteCam: {datos['NoteCam']}")
            
        return "\n".join(lineas)
    except:
        # Si no es JSON, usar el texto directamente
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
    
    print(f"Texto formateado:\n{texto_formateado}")  # Debug

    # --- CONFIGURACIÓN DEL RECUADRO ---
    ancho_recuadro = int(ancho * 0.85)  # 85% del ancho de la imagen
    padding = 25
    ancho_texto_disponible = ancho_recuadro - (padding * 2)

    # Tamaño de fuente más pequeño para mejor legibilidad
    try:
        fuente_titulo = ImageFont.truetype(FONT_PATH, 28)
        fuente_texto = ImageFont.truetype(FONT_PATH, 22)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()

    # Calcular altura necesaria para todo el texto
    lineas = texto_formateado.split('\n')
    alto_total_texto = 0
    
    # Usar fuente más grande para la primera línea (título)
    for i, linea in enumerate(lineas):
        if i == 0:
            bbox = fuente_titulo.getbbox(linea)
            alto_total_texto += bbox[3] - bbox[1] + 8
        else:
            bbox = fuente_texto.getbbox(linea)
            alto_total_texto += bbox[3] - bbox[1] + 5
    
    alto_recuadro = alto_total_texto + (padding * 2)

    # Posición - INFERIOR IZQUIERDA
    margen = 30
    x1 = margen
    y1 = alto - alto_recuadro - margen
    x2 = x1 + ancho_recuadro
    y2 = alto - margen

    # Crear capa para el recuadro
    capa_recuadro = Image.new('RGBA', img.size, (255, 255, 255, 0))
    dibujo = ImageDraw.Draw(capa_recuadro)
    
    # Dibujar recuadro semitransparente
    dibujo.rectangle(((x1, y1), (x2, y2)), fill=(0, 0, 0, 200))  # Fondo negro semitransparente
    
    # Dibujar el texto línea por línea
    y_offset = y1 + padding
    
    for i, linea in enumerate(lineas):
        if not linea.strip():
            y_offset += 20
            continue
            
        if i == 0:
            # Primera línea (título) con color especial
            dibujo.text((x1 + padding, y_offset), linea, font=fuente_titulo, fill=(255, 255, 100, 255))
            bbox = fuente_titulo.getbbox(linea)
            y_offset += (bbox[3] - bbox[1]) + 10
        else:
            # Resto de líneas
            # Dividir líneas largas si es necesario
            linea_actual = linea
            while True:
                bbox = fuente_texto.getbbox(linea_actual)
                ancho_linea = bbox[2] - bbox[0]
                if ancho_linea <= ancho_texto_disponible:
                    dibujo.text((x1 + padding, y_offset), linea_actual, font=fuente_texto, fill=(255, 255, 255, 255))
                    bbox = fuente_texto.getbbox(linea_actual)
                    y_offset += (bbox[3] - bbox[1]) + 8
                    break
                else:
                    # Cortar la línea
                    palabras = linea_actual.split(' ')
                    linea_corta = ""
                    for palabra in palabras:
                        prueba = linea_corta + " " + palabra if linea_corta else palabra
                        bbox = fuente_texto.getbbox(prueba)
                        if (bbox[2] - bbox[0]) <= ancho_texto_disponible:
                            linea_corta = prueba
                        else:
                            if linea_corta:
                                dibujo.text((x1 + padding, y_offset), linea_corta, font=fuente_texto, fill=(255, 255, 255, 255))
                                bbox = fuente_texto.getbbox(linea_corta)
                                y_offset += (bbox[3] - bbox[1]) + 8
                            linea_corta = palabra
                    linea_actual = linea_corta
                    continue
                break

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
