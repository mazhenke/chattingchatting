import os
import uuid
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db, socketio
from routes.upload import validate_image
from models.chat_room import ChatRoom
from models.room_member import RoomMember
from models.join_request import JoinRequest
from models.message import Message
from services.permissions import (
    can_create_room, can_enter_rooms, is_room_manager, is_room_creator, is_room_member,
)

room_bp = Blueprint('room', __name__, url_prefix='/api/rooms')


@room_bp.route('', methods=['GET'])
@login_required
def list_rooms():
    rooms = ChatRoom.query.all()
    return jsonify([r.to_dict() for r in rooms])


@room_bp.route('', methods=['POST'])
@login_required
def create_room():
    if not can_create_room(current_user.id):
        return jsonify(error='无法创建聊天室（已有聊天室或被禁止）'), 403

    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or len(name) > 64:
        return jsonify(error='聊天室名称不合法'), 400

    room = ChatRoom(name=name, creator_id=current_user.id)
    db.session.add(room)
    db.session.flush()

    member = RoomMember(room_id=room.id, user_id=current_user.id, role='creator')
    db.session.add(member)
    db.session.commit()

    return jsonify(room.to_dict()), 201


@room_bp.route('/<int:room_id>/icon', methods=['POST'])
@login_required
def upload_room_icon(room_id):
    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify(error='聊天室不存在'), 404
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    if 'file' not in request.files:
        return jsonify(error='没有上传文件'), 400
    file = request.files['file']
    file_data = file.read()
    if len(file_data) > 5 * 1024 * 1024:
        return jsonify(error='图标不能超过5MB'), 400

    ext = validate_image(file_data)
    if not ext or ext == 'gif':
        return jsonify(error='图标仅支持 JPG/PNG/WEBP 格式'), 400

    filename = f'room_{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'wb') as f:
        f.write(file_data)

    room.icon = f'/uploads/{filename}'
    db.session.commit()
    return jsonify(icon=room.icon)


@room_bp.route('/<int:room_id>', methods=['DELETE'])
@login_required
def dissolve_room(room_id):
    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify(error='聊天室不存在'), 404
    if room.creator_id != current_user.id and not current_user.is_admin:
        return jsonify(error='只有创建者或管理员可以解散聊天室'), 403

    socketio.emit('room_dissolved', {'room_id': room_id}, room=f'room_{room_id}')

    db.session.delete(room)
    db.session.commit()
    return jsonify(success=True)


@room_bp.route('/<int:room_id>/members', methods=['GET'])
@login_required
def list_members(room_id):
    members = RoomMember.query.filter_by(room_id=room_id).all()
    return jsonify([m.to_dict() for m in members])


@room_bp.route('/<int:room_id>/join', methods=['POST'])
@login_required
def join_room(room_id):
    if not can_enter_rooms(current_user.id):
        return jsonify(error='您已被禁止进入聊天室'), 403

    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify(error='聊天室不存在'), 404

    if is_room_member(current_user.id, room_id):
        return jsonify(error='您已是该聊天室成员'), 400

    existing = JoinRequest.query.filter_by(
        room_id=room_id, user_id=current_user.id, status='pending'
    ).first()
    if existing:
        return jsonify(error='您已提交加入申请，请等待审核'), 400

    # Reset rejected request if exists
    rejected = JoinRequest.query.filter_by(
        room_id=room_id, user_id=current_user.id, status='rejected'
    ).first()
    if rejected:
        rejected.status = 'pending'
        rejected.created_at = datetime.now(timezone.utc)
    else:
        jr = JoinRequest(room_id=room_id, user_id=current_user.id)
        db.session.add(jr)

    db.session.commit()

    jr = JoinRequest.query.filter_by(
        room_id=room_id, user_id=current_user.id, status='pending'
    ).first()
    socketio.emit('join_request_received', {
        'room_id': room_id,
        'request': jr.to_dict(),
    }, room=f'room_{room_id}')

    return jsonify(success=True, message='加入申请已提交')


@room_bp.route('/<int:room_id>/requests', methods=['GET'])
@login_required
def list_requests(room_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403
    requests_list = JoinRequest.query.filter_by(room_id=room_id, status='pending').all()
    return jsonify([r.to_dict() for r in requests_list])


@room_bp.route('/<int:room_id>/requests/<int:req_id>/approve', methods=['POST'])
@login_required
def approve_request(room_id, req_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    jr = db.session.get(JoinRequest, req_id)
    if not jr or jr.room_id != room_id or jr.status != 'pending':
        return jsonify(error='申请不存在或已处理'), 404

    jr.status = 'approved'
    member = RoomMember(room_id=room_id, user_id=jr.user_id, role='member')
    db.session.add(member)
    db.session.commit()

    socketio.emit('join_approved', {'room_id': room_id}, room=f'user_{jr.user_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/requests/<int:req_id>/reject', methods=['POST'])
@login_required
def reject_request(room_id, req_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    jr = db.session.get(JoinRequest, req_id)
    if not jr or jr.room_id != room_id or jr.status != 'pending':
        return jsonify(error='申请不存在或已处理'), 404

    jr.status = 'rejected'
    db.session.commit()

    socketio.emit('join_rejected', {'room_id': room_id}, room=f'user_{jr.user_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/invite', methods=['POST'])
@login_required
def invite_user(room_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    data = request.get_json()
    username = data.get('username', '').strip()

    from models.user import User
    target = User.query.filter_by(username=username).first()
    if not target:
        return jsonify(error='用户不存在'), 404

    if is_room_member(target.id, room_id):
        return jsonify(error='该用户已是聊天室成员'), 400

    if not can_enter_rooms(target.id):
        return jsonify(error='该用户已被禁止进入聊天室'), 403

    member = RoomMember(room_id=room_id, user_id=target.id, role='member')
    db.session.add(member)

    # Clear any pending join request
    jr = JoinRequest.query.filter_by(room_id=room_id, user_id=target.id, status='pending').first()
    if jr:
        jr.status = 'approved'

    db.session.commit()

    socketio.emit('join_approved', {'room_id': room_id}, room=f'user_{target.id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/kick/<int:user_id>', methods=['POST'])
@login_required
def kick_user(room_id, user_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    member = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
    if not member:
        return jsonify(error='用户不在聊天室中'), 404

    if member.role == 'creator':
        return jsonify(error='无法踢出创建者'), 403

    db.session.delete(member)
    db.session.commit()

    socketio.emit('user_kicked', {
        'room_id': room_id,
        'user_id': user_id,
    }, room=f'room_{room_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/mute/<int:user_id>', methods=['POST'])
@login_required
def mute_user(room_id, user_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    member = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
    if not member:
        return jsonify(error='用户不在聊天室中'), 404

    if member.role == 'creator':
        return jsonify(error='无法禁言创建者'), 403

    data = request.get_json() or {}
    duration_minutes = data.get('duration_minutes')

    member.is_muted = True
    if duration_minutes is not None:
        duration_minutes = min(int(duration_minutes), 525600)  # max 1 year
        member.mute_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    else:
        member.mute_until = None  # permanent

    db.session.commit()

    socketio.emit('user_muted', {
        'room_id': room_id,
        'user_id': user_id,
        'is_muted': True,
        'mute_until': member.mute_until.isoformat() if member.mute_until else None,
    }, room=f'room_{room_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/unmute/<int:user_id>', methods=['POST'])
@login_required
def unmute_user(room_id, user_id):
    if not is_room_manager(current_user.id, room_id):
        return jsonify(error='没有权限'), 403

    member = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
    if not member:
        return jsonify(error='用户不在聊天室中'), 404

    member.is_muted = False
    member.mute_until = None
    db.session.commit()

    socketio.emit('user_muted', {
        'room_id': room_id,
        'user_id': user_id,
        'is_muted': False,
        'mute_until': None,
    }, room=f'room_{room_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/leave', methods=['POST'])
@login_required
def leave_room(room_id):
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if not member:
        return jsonify(error='您不在该聊天室中'), 404

    if member.role == 'creator':
        # Creator leaving dissolves the room
        room = db.session.get(ChatRoom, room_id)
        socketio.emit('room_dissolved', {'room_id': room_id}, room=f'room_{room_id}')
        db.session.delete(room)
        db.session.commit()
        return jsonify(success=True, dissolved=True)

    db.session.delete(member)
    db.session.commit()

    socketio.emit('user_left', {
        'room_id': room_id,
        'user_id': current_user.id,
        'nickname': current_user.nickname,
    }, room=f'room_{room_id}')

    return jsonify(success=True)


@room_bp.route('/<int:room_id>/manager/<int:user_id>', methods=['POST'])
@login_required
def toggle_manager(room_id, user_id):
    if not is_room_creator(current_user.id, room_id):
        return jsonify(error='只有创建者可以设置管理者'), 403

    member = RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first()
    if not member:
        return jsonify(error='用户不在聊天室中'), 404

    if member.role == 'creator':
        return jsonify(error='无法修改创建者角色'), 403

    member.role = 'member' if member.role == 'manager' else 'manager'
    db.session.commit()

    return jsonify(success=True, role=member.role)


@room_bp.route('/<int:room_id>/online', methods=['GET'])
@login_required
def get_online_users(room_id):
    if not is_room_member(current_user.id, room_id):
        return jsonify(error='您不是该聊天室成员'), 403
    from sockets.chat_events import connected_users
    members = RoomMember.query.filter_by(room_id=room_id).all()
    online_ids = [m.user_id for m in members if m.user_id in connected_users]
    return jsonify(online_ids=online_ids)


@room_bp.route('/<int:room_id>/messages', methods=['GET'])
@login_required
def get_messages(room_id):
    if not is_room_member(current_user.id, room_id):
        return jsonify(error='您不是该聊天室成员'), 403

    before_id = request.args.get('before', type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)

    query = Message.query.filter_by(room_id=room_id)
    if before_id:
        query = query.filter(Message.id < before_id)
    messages = query.order_by(Message.id.desc()).limit(limit).all()
    messages.reverse()

    return jsonify([m.to_dict() for m in messages])
