from datetime import datetime, timezone

from extensions import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    msg_type = db.Column(db.String(16), default='text')  # 'text', 'image', 'emoji'
    content = db.Column(db.Text, nullable=False)
    is_recalled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'nickname': self.user_obj.nickname if self.user_obj else None,
            'avatar': self.user_obj.avatar if self.user_obj else None,
            'msg_type': self.msg_type,
            'content': '' if self.is_recalled else self.content,
            'is_recalled': self.is_recalled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
