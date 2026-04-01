import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, current_user
import requests as http_req

from extensions import db, socketio
from models.user import User
from services.nickname import fetch_random_nickname


def _get_timezone_from_ip(ip):
    """通过 IP 地址查询时区，查询失败时返回 'UTC'。"""
    try:
        # 本地/私有地址无法查询，直接返回 UTC
        if not ip or ip in ('127.0.0.1', '::1'):
            return 'UTC'
        for prefix in ('10.', '172.16.', '172.17.', '172.18.', '172.19.',
                        '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                        '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                        '172.30.', '172.31.', '192.168.'):
            if ip.startswith(prefix):
                return 'UTC'
        resp = http_req.get(
            f'http://ip-api.com/json/{ip}?fields=timezone',
            timeout=2
        )
        if resp.ok:
            tz = resp.json().get('timezone', '')
            if tz:
                return tz
    except Exception:
        pass
    return 'UTC'

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))
    return render_template('register.html')


@auth_bp.route('/register/step1', methods=['POST'])
def register_step1():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    valid, msg = User.validate_username(username)
    if not valid:
        return jsonify(error=msg), 400

    if not email or '@' not in email:
        return jsonify(error='邮箱格式不正确'), 400

    valid, msg = User.validate_password(password)
    if not valid:
        return jsonify(error=msg), 400

    # Advisory uniqueness check
    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        if existing.username == username:
            return jsonify(error='用户名已被使用'), 409
        return jsonify(error='邮箱已被使用'), 409

    session['reg_step1_passed'] = {
        'username': username,
        'email': email,
        'password': password
    }
    return jsonify(valid=True)


@auth_bp.route('/register/step2', methods=['POST'])
def register_step2():
    nickname = fetch_random_nickname()
    return jsonify(nickname=nickname)


@auth_bp.route('/register/confirm', methods=['POST'])
def register_confirm():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    nickname = data.get('nickname', '').strip()

    # Flow bypass check
    s_data = session.get('reg_step1_passed')
    if not s_data or s_data['username'] != username or s_data['email'] != email or s_data['password'] != password:
        return jsonify(error='请先完成注册第一步'), 400

    # Re-validate everything
    valid, msg = User.validate_username(username)
    if not valid:
        return jsonify(error=msg), 400

    valid, msg = User.validate_password(password)
    if not valid:
        return jsonify(error=msg), 400

    valid, msg = User.validate_nickname(nickname)
    if not valid:
        return jsonify(error=msg), 400

    if not email or '@' not in email:
        return jsonify(error='邮箱格式不正确'), 400

    try:
        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            nickname=nickname,
        )
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(error='用户名或邮箱已被使用'), 409

    return jsonify(success=True, message='注册成功')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        login_id = data.get('login_id', '').strip()
        password = data.get('password', '')
        
        # Allow login by username or email
        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id)
        ).first()

        if not user or not user.check_password(password):
            return jsonify(error='用户名/邮箱或密码错误'), 401
        # Kick previous sessions
        if user.current_session_id:
            socketio.emit('force_logout', {
                'message': '您的账号在别处登录，您已被挤下线。',
                'reason': 'new_login'
            }, room=f'user_{user.id}')

        # Update session info
        new_sid = uuid.uuid4().hex
        user.current_session_id = new_sid
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = request.remote_addr
        db.session.commit()

        session['session_id'] = new_sid
        session['user_timezone'] = _get_timezone_from_ip(request.remote_addr)
        login_user(user)
        return jsonify(success=True, redirect=url_for('chat.chat_page'))

    # GET request
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
