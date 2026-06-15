import os
import gdown
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, request, send_file
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import io
import base64
import csv

# --- CONFIGURACIÓN DE MEMORIA ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Función para descargar el modelo desde Drive
def descargar_y_cargar_modelo():
    modelo_path = 'modelo_ecografias.keras'
    if not os.path.exists(modelo_path):
        url = 'TU_ID_DE_DRIVE_AQUI' # <--- Asegúrate de poner tu ID real
        gdown.download(id=url, output=modelo_path, quiet=False)
    return load_model(modelo_path)

# Cargar el modelo al INICIO (fuera de la función index)
modelo = descargar_y_cargar_modelo()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        caravana = request.form['caravana']
        archivo = request.files['archivo']
        
        # Procesar imagen
        img = image.load_img(io.BytesIO(archivo.read()), target_size=(224, 224))
        x = image.img_to_array(img) / 255.0
        x = np.expand_dims(x, axis=0)
        
        # Predicción
        pred = modelo.predict(x)
        resultado = "Preñada" if pred[0][0] > 0.5 else "Vacía"
        confianza = round(float(pred[0][0] * 100 if pred[0][0] > 0.5 else (1 - pred[0][0]) * 100), 2)
        
        # Guardar en CSV
        with open('historial.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([caravana, resultado, confianza])
            
        return render_template('index.html', resultado=resultado, confianza=confianza)
    
    return render_template('index.html')

@app.route('/descargar_excel')
def descargar_excel():
    return send_file('historial.csv', as_attachment=True)

if __name__ == '__main__':
    app.run()
