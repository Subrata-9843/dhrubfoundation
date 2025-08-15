import os
import uuid
from werkzeug.utils import secure_filename
from app import app

def save_uploaded_file(file, folder):
    """Save uploaded file to specified folder"""
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(folder, unique_name)
    file.save(filepath)
    return unique_name

def delete_file(filepath):
    """Delete file from filesystem"""
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']