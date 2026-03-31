import sys
import os
import getpass
from datetime import datetime

from flask import Flask, session, redirect, url_for, request
from flask_login import current_user, logout_user

from config import Config
from extensions import db, login_manager, socketio


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*')
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return db.session.get(User, int(user_id))

    @app.before_request
    def check_session_validity():
        """Ensure the user's current session matches the one in the database."""
        # Skip for static files and auth routes to avoid redirect loops or blocking login
        if not request.endpoint or 'static' in request.endpoint or \
           request.endpoint in ('auth.login', 'auth.logout', 'auth.register_step1', 'auth.register_step2', 'auth.register_confirm'):
            return

        if current_user.is_authenticated:
            # Check for current_session_id in flask session
            s_id = session.get('session_id')
            if not s_id or s_id != current_user.current_session_id:
                logout_user()
                session.clear()
                return redirect(url_for('auth.login'))

    from routes.auth import auth_bp
    from routes.chat import chat_bp
    from routes.room import room_bp
    from routes.user import user_bp
    from routes.upload import upload_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(room_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_bp)

    from sockets import register_socket_handlers
    register_socket_handlers(socketio)

    with app.app_context():
        import models  # noqa: F401
        db.create_all()

    return app


def create_admin():
    """Create an admin user via CLI prompts."""
    app = create_app()
    with app.app_context():
        from models.user import User

        existing_admin = User.query.filter_by(is_admin=True).first()
        if existing_admin:
            print(f'提示: 已存在管理员账号 "{existing_admin.username}"。')
            cont = input('是否继续创建新的管理员? (y/N): ').lower()
            if cont != 'y':
                sys.exit(0)

        print('=== 创建管理员账号 ===')
        username = input('用户名: ').strip()
        valid, msg = User.validate_username(username)
        if not valid:
            print(f'错误: {msg}')
            sys.exit(1)

        email = input('邮箱: ').strip()
        if not email or '@' not in email:
            print('错误: 邮箱格式不正确')
            sys.exit(1)

        password = getpass.getpass('密码 (至少6位): ')
        valid, msg = User.validate_password(password)
        if not valid:
            print(f'错误: {msg}')
            sys.exit(1)

        nickname = input('昵称 (最多24字符): ').strip()
        valid, msg = User.validate_nickname(nickname)
        if not valid:
            print(f'错误: {msg}')
            sys.exit(1)

        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            print('错误: 用户名或邮箱已存在')
            sys.exit(1)

        admin = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            nickname=nickname,
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f'管理员 "{username}" 创建成功!')


if __name__ == '__main__':
    if '--create-admin' in sys.argv:
        create_admin()
    else:
        app = create_app()
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
