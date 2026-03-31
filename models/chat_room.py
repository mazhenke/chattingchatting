from datetime import datetime, timezone

from extensions import db


class ChatRoom(db.Model):
    __tablename__ = 'chat_rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    icon = db.Column(db.String(256), nullable=True)  # path to room icon image
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('RoomMember', backref='room', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='room', cascade='all, delete-orphan')
    join_requests = db.relationship('JoinRequest', backref='room', cascade='all, delete-orphan')
    permissions = db.relationship('UserPermission', backref='room', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'creator_id': self.creator_id,
            'creator_name': self.creator.nickname if self.creator else None,
            'member_count': len(self.members),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
