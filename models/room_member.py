from datetime import datetime, timezone

from extensions import db


class RoomMember(db.Model):
    __tablename__ = 'room_members'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(16), default='member')  # 'creator', 'manager', 'member'
    is_muted = db.Column(db.Boolean, default=False)
    mute_until = db.Column(db.DateTime, nullable=True)  # null = permanent if is_muted
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', name='uq_room_user'),
    )

    def is_currently_muted(self):
        if not self.is_muted:
            return False
        if self.mute_until is None:
            return True  # permanent
        return datetime.utcnow() < self.mute_until

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'nickname': self.user.nickname if self.user else None,
            'username': self.user.username if self.user else None,
            'avatar': self.user.avatar if self.user else None,
            'role': self.role,
            'is_muted': self.is_currently_muted(),
            'mute_until': self.mute_until.isoformat() if self.mute_until else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
        }
