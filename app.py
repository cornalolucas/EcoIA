import os
import gdown
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, request, send_file
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import io
import csv
import gc
import urllib.parse 

# Limitar TensorFlow a la CPU para mayor estabilidad en el servidor
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

def get_model():
    model_path = 'modelo_ecografias.keras'
    
    # ¡Aquí está tu ID real de Google Drive integrado!
    url = '1rI0jWI7-JW_w6BqZWRozqa66YZqkfzUA' 
    
    if not os.path.exists(model_path):
        gdown.download(id=url, output=model_path, quiet=False)
    return load_model(model_path)

# Carga única global para no saturar la memoria
model = get_model()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'archivo' not in request.files: return "No file", 400
        archivo = request.files['archivo']
        caravana = request.form.get('caravana', 'N/A')
        
        try:
            # Procesar imagen
            img = image.load_img(io.BytesIO(archivo.read()), target_size=(224, 224))
            x = image.img_to_array(img) / 255.0
            x = np.expand_dims(x, axis=0)
            
            # Predicción
            pred = model.predict(x)
            resultado = "Preñada" if pred[0][0] > 0.5 else "Vacía"
            confianza = round(float(pred[0][0] * 100 if pred[0][0] > 0.5 else (1 - pred[0][0]) * 100), 2)
            
            # Guardar en historial
            with open('historial.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([caravana, resultado, confianza])
            
            # Crear mensaje de WhatsApp
            mensaje_wa = f"🔬 *EcoDiagnóstico Bovino*\n🐄 Caravana: {caravana}\n📊 Resultado: *{resultado}*\n🎯 Confianza: {confianza}%\n\n_Generado por EcoIA_"
            wa_link = urllib.parse.quote(mensaje_wa) 
            
            # Limpiar memoria
            gc.collect()
            
            return render_template('index.html', resultado=resultado, confianza=confianza, caravana=caravana, wa_link=wa_link)
        
        except Exception as e:
            return f"Error en procesamiento: {str(e)}", 500
            
    return render_template('index.html')

@app.route('/descargar_reporte')
def descargar_reporte():
    return send_file('historial.csv', as_attachment=True)

if __name__ == '__main__':
    app.run()
