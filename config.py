import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Directorios
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    CONVERTED_FOLDER = os.path.join(basedir, 'converted')

    # Extensiones permitidas
    ALLOWED_EXTENSIONS = {'wav', 'flac', 'ogg', 'mp3', 'aac', 'm4a'}

    # Tamaño máximo total de archivos (1GB)
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024
