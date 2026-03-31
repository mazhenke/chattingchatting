from models.permission import UserPermission
from models.room_member import RoomMember
from models.chat_room import ChatRoom


def can_enter_rooms(user_id):
    """Check if user is banned from all rooms."""
    ban = UserPermission.query.filter_by(
        user_id=user_id, permission_type='ban_all_rooms'
    ).first()
    return ban is None


def can_create_room(user_id):
    """Check if user can create a room."""
    if not can_enter_rooms(user_id):
        return False
    ban = UserPermission.query.filter_by(
        user_id=user_id, permission_type='ban_create_room'
    ).first()
    if ban:
        return False
    existing = ChatRoom.query.filter_by(creator_id=user_id).first()
    return existing is None


def can_speak(user_id, room_id):
    """Check if user can speak in a specific room."""
    # Check global bans
    global_ban = UserPermission.query.filter_by(
        user_id=user_id, permission_type='ban_speak'
    ).first()
    if global_ban:
        return False

    # Check room-specific ban
    room_ban = UserPermission.query.filter(
        UserPermission.user_id == user_id,
        UserPermission.permission_type == 'ban_room',
        UserPermission.room_id == room_id,
    ).first()
    if room_ban:
        return False

    if not can_enter_rooms(user_id):
        return False

    # Check membership and mute status
    member = RoomMember.query.filter_by(
        room_id=room_id, user_id=user_id
    ).first()
    if not member:
        return False
    if member.is_currently_muted():
        return False

    return True


def is_room_manager(user_id, room_id):
    """Check if user is a manager or creator of the room."""
    member = RoomMember.query.filter_by(
        room_id=room_id, user_id=user_id
    ).first()
    return member is not None and member.role in ('creator', 'manager')


def is_room_creator(user_id, room_id):
    """Check if user is the creator of the room."""
    member = RoomMember.query.filter_by(
        room_id=room_id, user_id=user_id
    ).first()
    return member is not None and member.role == 'creator'


def is_room_member(user_id, room_id):
    """Check if user is a member of the room."""
    member = RoomMember.query.filter_by(
        room_id=room_id, user_id=user_id
    ).first()
    return member is not None
