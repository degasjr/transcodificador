import os
import time
import zipfile
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
from config import Config

"""
Esta es una web app que convierte archivos de audio al formato Opus
Autor: Alexis Adam
Repositorio: github.com/degasjr
"""

app = Flask(__name__)
app.config.from_object(Config)

# Asegurar que existen los directorios
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONVERTED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def convert_to_opus(input_path, output_path):
    """Convierte un archivo a Opus usando opusenc"""
    cmd = f"opusenc --quiet --comment COMMENT=github.com/degasjr '{input_path}' '{output_path}'"
    return os.system(cmd)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_files():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No se seleccionaron archivos'}), 400
        
        files = request.files.getlist('files')
        if len(files) == 0:
            return jsonify({'error': 'No se seleccionaron archivos'}), 400
        
        # Validar tamaño total de los archivos (ej. 100MB máximo)
        total_size = sum(f.content_length for f in files if f.content_length)
        if total_size > 1000 * 1024 * 1024:  # 1GB
            return jsonify({'error': 'El tamaño total de los archivos excede el límite de 100MB'}), 400

        # Filtrar archivos permitidos
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        if not valid_files:
            return jsonify({'error': 'Ningún archivo tiene un formato válido'}), 400

        # Procesar en lotes de 50 archivos
        batch_size = 50
        batches = [valid_files[i:i + batch_size] for i in range(0, len(valid_files), batch_size)]
        results = []
        
        for batch in batches:
            batch_results = []
            for file in batch:
                try:
                    # Guardar archivo subido
                    filename = secure_filename(file.filename)
                    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(input_path)
                    
                    # Crear nombre para el archivo convertido
                    base_name = os.path.splitext(filename)[0]
                    output_filename = f"{base_name}.opus"
                    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
                    
                    # Convertir a Opus
                    return_code = os.system(f"opusenc --quiet --comment COMMENT=github.com/degasjr '{input_path}' '{output_path}'")
                    
                    if return_code == 0:
                        batch_results.append({
                            'original': filename,
                            'converted': output_filename,
                            'success': True
                        })
                    else:
                        batch_results.append({
                            'original': filename,
                            'error': 'Error en la conversión',
                            'success': False
                        })
                    
                    # Eliminar archivo subido
                    if os.path.exists(input_path):
                        os.unlink(input_path)
                    
                    # Pequeño delay para aliviar la carga del servidor
                    time.sleep(1)
                    
                except Exception as e:
                    batch_results.append({
                        'original': file.filename,
                        'error': str(e),
                        'success': False
                    })
            
            results.extend(batch_results)
        
        # Si hay más de un archivo exitoso, crear un ZIP
        successful_conversions = [r for r in results if r['success']]
        download_filename = None
        
        if len(successful_conversions) > 1:
            zip_filename = 'converted_files.zip'
            zip_path = os.path.join(app.config['CONVERTED_FOLDER'], zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for item in successful_conversions:
                    file_path = os.path.join(app.config['CONVERTED_FOLDER'], item['converted'])
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=item['converted'])
            
            download_filename = zip_filename
        
        return jsonify({
            'results': results,
            'download_all': download_filename,
            'success_count': len(successful_conversions)
        })

    except Exception as e:
        app.logger.error(f"Error en convert_files: {str(e)}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404

    return send_file(file_path, as_attachment=True)

# Configurar función para limpiar después de la descarga
@app.route('/cleanup', methods=['POST'])
def cleanup():
    try:
        # Limpiar directorio de uploads
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                app.logger.error(f"Error al eliminar {file_path}: {e}")

        # Limpiar directorio de converted
        for filename in os.listdir(app.config['CONVERTED_FOLDER']):
            file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                app.logger.error(f"Error al eliminar {file_path}: {e}")

        return jsonify({'success': True}), 200, {'Content-Type': 'application/json'}
    
    except Exception as e:
        app.logger.error(f"Error en cleanup: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500, {'Content-Type': 'application/json'}

if __name__ == '__main__':
    app.run(debug=True)
