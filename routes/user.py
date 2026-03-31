import os
import uuid

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user, logout_user

from extensions import db, socketio
from models.user import User
from models.chat_room import ChatRoom
from services.nickname import fetch_random_nickname
from routes.upload import validate_image

user_bp = Blueprint('user', __name__, url_prefix='/api/users')


@user_bp.route('/me', methods=['GET'])
@login_required
def get_profile():
    return jsonify(current_user.to_dict())


@user_bp.route('/me', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()

    if 'username' in data:
        username = data['username'].strip()
        valid, msg = User.validate_username(username)
        if not valid:
            return jsonify(error=msg), 400
        if username != current_user.username:
            existing = User.query.filter_by(username=username).first()
            if existing:
                return jsonify(error='用户名已被使用'), 409
            current_user.username = username

    if 'email' in data:
        email = data['email'].strip()
        if not email or '@' not in email:
            return jsonify(error='邮箱格式不正确'), 400
        if email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                return jsonify(error='邮箱已被使用'), 409
            current_user.email = email

    if 'password' in data:
        password = data['password']
        valid, msg = User.validate_password(password)
        if not valid:
            return jsonify(error=msg), 400
        current_user.password_hash = User.hash_password(password)

    db.session.commit()
    return jsonify(current_user.to_dict())


@user_bp.route('/me/nickname', methods=['POST'])
@login_required
def update_nickname():
    data = request.get_json() or {}
    nickname = data.get('nickname', '').strip()

    if data.get('random'):
        nickname = fetch_random_nickname()
    else:
        valid, msg = User.validate_nickname(nickname)
        if not valid:
            return jsonify(error=msg), 400

    current_user.nickname = nickname
    db.session.commit()
    return jsonify(nickname=nickname)


@user_bp.route('/me/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'file' not in request.files:
        return jsonify(error='没有上传文件'), 400
    file = request.files['file']
    if not file.filename:
        return jsonify(error='文件名为空'), 400

    file_data = file.read()
    if len(file_data) > 5 * 1024 * 1024:  # 5MB for avatars
        return jsonify(error='头像文件不能超过5MB'), 400

    ext = validate_image(file_data)
    if not ext or ext == 'gif':  # no animated avatars
        return jsonify(error='头像仅支持 JPG/PNG/WEBP 格式'), 400

    filename = f'avatar_{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'wb') as f:
        f.write(file_data)

    current_user.avatar = f'/uploads/{filename}'
    db.session.commit()
    return jsonify(avatar=current_user.avatar)


@user_bp.route('/me', methods=['DELETE'])
@login_required
def delete_account():
    user = current_user._get_current_object()

    # If user has a created room, dissolve it
    room = ChatRoom.query.filter_by(creator_id=user.id).first()
    if room:
        socketio.emit('room_dissolved', {'room_id': room.id}, room=f'room_{room.id}')
        db.session.delete(room)

    logout_user()
    db.session.delete(user)
    db.session.commit()
    return jsonify(success=True)
