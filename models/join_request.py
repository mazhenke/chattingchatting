from datetime import datetime, timezone

from extensions import db


class JoinRequest(db.Model):
    __tablename__ = 'join_requests'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(16), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='join_requests')

    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', name='uq_join_request'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'nickname': self.user.nickname if self.user else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
