import os
import uuid

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_login import login_required

upload_bp = Blueprint('upload', __name__)

# Magic bytes for image validation
IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',  # RIFF....WEBP
}


def validate_image(file_data):
    """Validate image by checking magic bytes."""
    for sig, ext in IMAGE_SIGNATURES.items():
        if file_data[:len(sig)] == sig:
            if ext == 'webp':
                # Additional check for WEBP
                if file_data[8:12] != b'WEBP':
                    continue
            return ext
    return None


@upload_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify(error='没有上传文件'), 400

    file = request.files['file']
    if not file.filename:
        return jsonify(error='文件名为空'), 400

    file_data = file.read()
    if len(file_data) > current_app.config['MAX_UPLOAD_SIZE']:
        return jsonify(error='文件大小超过10MB限制'), 400

    ext = validate_image(file_data)
    if not ext:
        return jsonify(error='不支持的图片格式，仅支持 JPG/PNG/GIF/WEBP'), 400

    filename = f'{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'wb') as f:
        f.write(file_data)

    return jsonify(url=f'/uploads/{filename}')


@upload_bp.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
