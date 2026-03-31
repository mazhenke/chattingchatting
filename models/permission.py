from datetime import datetime, timezone

from extensions import db


class UserPermission(db.Model):
    __tablename__ = 'user_permissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    permission_type = db.Column(db.String(32), nullable=False)
    # 'ban_all_rooms', 'ban_create_room', 'ban_speak', 'ban_room', 'kick_room'
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=True)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], overlaps="permissions_received,target_user_obj")
    issuer = db.relationship('User', foreign_keys=[issued_by], overlaps="issuer_obj,permissions_issued")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permission_type': self.permission_type,
            'room_id': self.room_id,
            'issued_by': self.issued_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
