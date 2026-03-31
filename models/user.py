import hashlib
import re
from datetime import datetime, timezone

from flask_login import UserMixin

from extensions import db

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
NICKNAME_PATTERN = re.compile(
    r'^[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9 _\-~]+$'
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(64), nullable=False)
    nickname = db.Column(db.String(24), nullable=False)
    avatar = db.Column(db.String(256), nullable=True)  # path to avatar image
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_room = db.relationship('ChatRoom', backref='creator', uselist=False,
                                   foreign_keys='ChatRoom.creator_id')
    memberships = db.relationship('RoomMember', backref='user',
                                  foreign_keys='RoomMember.user_id',
                                  cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='user_obj',
                               foreign_keys='Message.user_id',
                               cascade='all, delete-orphan')
    permissions_issued = db.relationship('UserPermission', backref='issuer_obj',
                                         foreign_keys='UserPermission.issued_by')
    permissions_received = db.relationship('UserPermission', backref='target_user_obj',
                                           foreign_keys='UserPermission.user_id',
                                           cascade='all, delete-orphan')
    # join_requests is handled by backref in JoinRequest model

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == self.hash_password(password)

    @staticmethod
    def validate_username(username):
        if not username or len(username) > 32:
            return False, '用户名长度必须在1-32个字符之间'
        if not USERNAME_PATTERN.match(username):
            return False, '用户名只能包含字母、数字、下划线和连字符'
        return True, ''

    @staticmethod
    def validate_nickname(nickname):
        if not nickname or not nickname.strip():
            return False, '昵称不能为空'
        if len(nickname) > 24:
            return False, '昵称最多24个字符'
        if nickname != nickname.strip():
            return False, '昵称不能以空格开头或结尾'
        if '  ' in nickname:
            return False, '昵称不能包含连续空格'
        if not NICKNAME_PATTERN.match(nickname):
            return False, '昵称只能包含中文、字母、数字、空格和 _-~ 符号'
        return True, ''

    @staticmethod
    def validate_password(password):
        if not password or len(password) < 6:
            return False, '密码至少需要6个字符'
        return True, ''

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
