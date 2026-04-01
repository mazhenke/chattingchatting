from flask import Blueprint, render_template, redirect, url_for, session
from flask_login import login_required, current_user

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@chat_bp.route('/chat')
@login_required
def chat_page():
    user_timezone = session.get('user_timezone', 'UTC')
    return render_template('chat.html', user=current_user, user_timezone=user_timezone)
