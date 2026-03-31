from datetime import datetime, timezone, timedelta

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, disconnect

from extensions import socketio, db
from models.message import Message
from models.room_member import RoomMember
from services.permissions import can_speak, is_room_member, is_room_manager

# Map user_id -> set of session IDs
connected_users = {}


@socketio.on('connect')
def on_connect():
    if not current_user.is_authenticated:
        return False
    
    # Check session_id consistency for Socket connection
    s_id = session.get('session_id')
    if not s_id or s_id != current_user.current_session_id:
        return False

    uid = current_user.id
    was_offline = uid not in connected_users
    if uid not in connected_users:
        connected_users[uid] = set()
    connected_users[uid].add(request.sid)
    # Join a personal room for targeted messages
    join_room(f'user_{uid}')
    # Broadcast online status to all rooms the user is a member of
    if was_offline:
        members = RoomMember.query.filter_by(user_id=uid).all()
        for m in members:
            emit('presence_change', {'user_id': uid, 'online': True},
                 room=f'room_{m.room_id}', include_self=False)


@socketio.on('disconnect')
def on_disconnect():
    if not current_user.is_authenticated:
        return
    uid = current_user.id
    if uid in connected_users:
        connected_users[uid].discard(request.sid)
        if not connected_users[uid]:
            del connected_users[uid]
            # Broadcast offline status to all rooms the user is a member of
            members = RoomMember.query.filter_by(user_id=uid).all()
            for m in members:
                emit('presence_change', {'user_id': uid, 'online': False},
                     room=f'room_{m.room_id}')


@socketio.on('join_room')
def on_join_room(data):
    if not current_user.is_authenticated:
        return
    room_id = data.get('room_id')
    if not room_id or not is_room_member(current_user.id, room_id):
        emit('error', {'message': '您不是该聊天室成员'})
        return

    room_name = f'room_{room_id}'
    join_room(room_name)

    # Send recent message history
    messages = Message.query.filter_by(room_id=room_id).order_by(
        Message.id.desc()
    ).limit(50).all()
    messages.reverse()

    emit('message_history', {
        'room_id': room_id,
        'messages': [m.to_dict() for m in messages],
    })

    emit('user_joined', {
        'room_id': room_id,
        'user_id': current_user.id,
        'nickname': current_user.nickname,
    }, room=room_name, include_self=False)


@socketio.on('leave_room')
def on_leave_room(data):
    if not current_user.is_authenticated:
        return
    room_id = data.get('room_id')
    room_name = f'room_{room_id}'

    emit('user_left', {
        'room_id': room_id,
        'user_id': current_user.id,
        'nickname': current_user.nickname,
    }, room=room_name, include_self=False)

    leave_room(room_name)


@socketio.on('send_message')
def on_send_message(data):
    if not current_user.is_authenticated:
        return

    room_id = data.get('room_id')
    msg_type = data.get('msg_type', 'text')
    content = data.get('content', '').strip()

    if not room_id or not content:
        emit('error', {'message': '消息内容不能为空'})
        return

    if msg_type not in ('text', 'image', 'emoji'):
        emit('error', {'message': '不支持的消息类型'})
        return

    if not can_speak(current_user.id, room_id):
        emit('error', {'message': '您已被禁言或无权在此聊天室发言'})
        return

    message = Message(
        room_id=room_id,
        user_id=current_user.id,
        msg_type=msg_type,
        content=content,
    )
    db.session.add(message)
    db.session.commit()

    emit('new_message', message.to_dict(), room=f'room_{room_id}')


@socketio.on('recall_message')
def on_recall_message(data):
    if not current_user.is_authenticated:
        return

    message_id = data.get('message_id')
    if not message_id:
        emit('error', {'message': '无效的消息ID'})
        return

    message = db.session.get(Message, message_id)
    if not message:
        emit('error', {'message': '消息不存在'})
        return

    if message.is_recalled:
        return

    # Check permission: own message within 2 minutes, or room manager (no time limit)
    now = datetime.utcnow()
    is_own = message.user_id == current_user.id
    within_time = (now - message.created_at) < timedelta(minutes=2) if message.created_at else False

    if is_own and within_time:
        pass  # allowed
    elif is_room_manager(current_user.id, message.room_id):
        pass  # managers can recall anytime
    else:
        if is_own:
            emit('error', {'message': '超过2分钟，无法撤回'})
        else:
            emit('error', {'message': '没有权限撤回此消息'})
        return

    message.is_recalled = True
    db.session.commit()

    emit('message_recalled', {
        'message_id': message_id,
        'room_id': message.room_id,
    }, room=f'room_{message.room_id}')
