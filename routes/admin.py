from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps

from extensions import db, socketio
from models.user import User
from models.chat_room import ChatRoom
from models.room_member import RoomMember
from models.message import Message
from models.permission import UserPermission

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify(error='需要管理员权限'), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('')
@admin_required
def admin_page():
    return render_template('admin.html', user=current_user)


# --- Users API ---

@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()

    query = User.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            User.username.ilike(like) |
            User.email.ilike(like) |
            User.nickname.ilike(like)
        )

    pagination = query.order_by(User.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
    })


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error='用户不存在'), 404

    if user.id == current_user.id:
        return jsonify(error='不能删除自己'), 400

    # Dissolve user's created room if any
    room = ChatRoom.query.filter_by(creator_id=user.id).first()
    if room:
        socketio.emit('room_dissolved', {'room_id': room.id}, room=f'room_{room.id}')
        db.session.delete(room)

    db.session.delete(user)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/api/users/<int:user_id>/permission', methods=['POST'])
@admin_required
def add_permission(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error='用户不存在'), 404

    data = request.get_json()
    perm_type = data.get('permission_type')
    room_id = data.get('room_id')

    valid_types = {'ban_all_rooms', 'ban_create_room', 'ban_speak', 'ban_room', 'kick_room'}
    if perm_type not in valid_types:
        return jsonify(error='无效的权限类型'), 400

    if perm_type in ('ban_room', 'kick_room') and not room_id:
        return jsonify(error='需要指定聊天室'), 400

    perm = UserPermission(
        user_id=user_id,
        permission_type=perm_type,
        room_id=room_id,
        issued_by=current_user.id,
    )
    db.session.add(perm)
    db.session.commit()

    return jsonify(perm.to_dict()), 201


@admin_bp.route('/api/users/<int:user_id>/permission/<int:perm_id>', methods=['DELETE'])
@admin_required
def remove_permission(user_id, perm_id):
    perm = db.session.get(UserPermission, perm_id)
    if not perm or perm.user_id != user_id:
        return jsonify(error='权限不存在'), 404

    db.session.delete(perm)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/api/users/<int:user_id>/admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error='用户不存在'), 404

    if user.id == current_user.id:
        return jsonify(error='不能修改自己的管理员状态'), 400

    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify(success=True, is_admin=user.is_admin)


@admin_bp.route('/api/users/<int:user_id>/permissions', methods=['GET'])
@admin_required
def list_user_permissions(user_id):
    perms = UserPermission.query.filter_by(user_id=user_id).all()
    return jsonify([p.to_dict() for p in perms])


# --- Rooms API ---

@admin_bp.route('/api/rooms', methods=['GET'])
@admin_required
def list_rooms():
    rooms = ChatRoom.query.all()
    return jsonify([r.to_dict() for r in rooms])


@admin_bp.route('/api/rooms/<int:room_id>', methods=['DELETE'])
@admin_required
def force_dissolve_room(room_id):
    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify(error='聊天室不存在'), 404

    socketio.emit('room_dissolved', {'room_id': room_id}, room=f'room_{room_id}')
    db.session.delete(room)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/api/rooms/<int:room_id>/members', methods=['GET'])
@admin_required
def list_room_members(room_id):
    members = RoomMember.query.filter_by(room_id=room_id).all()
    return jsonify([m.to_dict() for m in members])


# --- Messages API ---

@admin_bp.route('/api/messages', methods=['GET'])
@admin_required
def list_messages():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    room_id = request.args.get('room_id', type=int)
    user_id = request.args.get('user_id', type=int)
    keyword = request.args.get('keyword', '').strip()

    query = Message.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if keyword:
        query = query.filter(Message.content.ilike(f'%{keyword}%'))

    pagination = query.order_by(Message.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'messages': [m.to_dict() for m in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
    })


@admin_bp.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@admin_required
def delete_message(msg_id):
    msg = db.session.get(Message, msg_id)
    if not msg:
        return jsonify(error='消息不存在'), 404

    db.session.delete(msg)
    db.session.commit()
    return jsonify(success=True)
