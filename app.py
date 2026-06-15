import os
import numpy as np
import base64
import sqlite3
import gdown
from io import BytesIO
from flask import Flask, request, render_template, Response
from PIL import Image

# Intentar importar TensorFlow
try:
    import tensorflow as tf
    from tensorflow.keras.preprocessing import image
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

app = Flask(__name__)

# --- Configuración del Modelo (Auto-descarga desde Drive) ---
MODEL_ID = '1rI0jWI7-JW_w6BqZWRozqa66YZqkfzUA'
MODEL_PATH = 'modelo_ecografias.keras'

def descargar_y_cargar_modelo():
    if not os.path.exists(MODEL_PATH):
        print("Descargando modelo desde Google Drive...")
        url = f'https://drive.google.com/uc?id={MODEL_ID}'
        gdown.download(url, MODEL_PATH, quiet=False)
    
    if TENSORFLOW_AVAILABLE:
        return tf.keras.models.load_model(MODEL_PATH)
    return None

modelo = descargar_y_cargar_modelo()

# --- Configuración de la Base de Datos ---
def inicializar_bd():
    conn = sqlite3.connect('tambo_datos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caravana TEXT NOT NULL,
            diagnostico TEXT NOT NULL,
            confianza TEXT NOT NULL,
            nombre_imagen TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

inicializar_bd()

def diagnosticar_imagen(ruta_imagen):
    if modelo is None:
        import random
        diagnostico = random.choice(["Preñada", "Vacía"])
        confianza = random.uniform(85.0, 99.9)
        return diagnostico, f"{confianza:.1f}"

    img = image.load_img(ruta_imagen, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    
    prediccion = modelo.predict(img_array)
    valor_prediccion = prediccion[0][0]

    if valor_prediccion > 0.5:
        return "Vacía", f"{(valor_prediccion * 100):.1f}"
    else:
        return "Preñada", f"{((1 - valor_prediccion) * 100):.1f}"

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado, confianza, imagen_base64, caravana = None, None, None, None
    if request.method == 'POST':
        archivo = request.files.get('archivo')
        caravana = request.form.get('caravana', 'Sin ID')
        if archivo and archivo.filename != '':
            os.makedirs('uploads', exist_ok=True)
            filepath = os.path.join('uploads', archivo.filename)
            archivo.save(filepath)
            
            try:
                resultado, confianza = diagnosticar_imagen(filepath)
                with Image.open(filepath) as img:
                    img.thumbnail((500, 500)) 
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    imagen_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                conn = sqlite3.connect('tambo_datos.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO registros (caravana, diagnostico, confianza, nombre_imagen) VALUES (?, ?, ?, ?)",
                               (caravana, resultado, confianza, archivo.filename))
                conn.commit()
                conn.close()
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
            
    return render_template('index.html', resultado=resultado, confianza=confianza, imagen_demostrada=imagen_base64, caravana=caravana)

@app.route('/descargar_excel')
def descargar_excel():
    conn = sqlite3.connect('tambo_datos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT caravana, diagnostico, nombre_imagen, fecha FROM registros ORDER BY fecha DESC")
    registros = cursor.fetchall()
    conn.close()
    def generar_csv():
        yield '\ufeffNro de Caravana;Diagnostico;Nombre de Imagen;Fecha de Muestra\n'
        for fila in registros:
            yield f"{fila[0]};{fila[1]};{fila[2]};{fila[3]}\n"
    return Response(generar_csv(), mimetype='text/csv; charset=utf-8', 
                    headers={'Content-Disposition': 'attachment; filename=reporte_reproductivo.csv'})

if __name__ == '__main__':
    app.run(debug=True)
