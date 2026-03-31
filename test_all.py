"""Comprehensive test suite for Anonymous Chat."""
import os
import sys

from app import create_app
app = create_app({
    'SECRET_KEY': 'test-secret',
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite://'
})
errors = []
test_count = 0

from extensions import db
from models.user import User
from models.message import Message
from models.permission import UserPermission
from routes.upload import validate_image
from services.permissions import can_create_room, can_speak, can_enter_rooms

def section(name):
    print(f"\n>>> SECTION: {name} " + "=" * (max(2, 40 - len(name))))

def check(name, condition):
    global test_count
    test_count += 1
    if condition:
        print(f"  [PASS] {name}")
    else:
        errors.append(name)
        print(f"  [FAIL] {name}")


with app.test_client() as c:
    section("Authentication")
    # === Auth ===
    r = c.post('/auth/register/step1', json={
        'username': 'testuser', 'email': 'test@test.com', 'password': '123456'
    })
    check('step1 valid', r.status_code == 200)

    with c.session_transaction() as sess:
        sess['reg_step1_passed'] = {
            'username': 'testuser', 'email': 'test@test.com', 'password': '123456'
        }

    r = c.post('/auth/register/confirm', json={
        'username': 'testuser', 'email': 'test@test.com',
        'password': '123456', 'nickname': '测试昵称'
    })
    check('register confirm', r.status_code == 200)

    # For duplicate username test
    with c.session_transaction() as sess:
        sess['reg_step1_passed'] = {
            'username': 'testuser', 'email': 'test2@test.com', 'password': '123456'
        }
    r = c.post('/auth/register/confirm', json={
        'username': 'testuser', 'email': 'test2@test.com',
        'password': '123456', 'nickname': '另一个'
    })
    check('duplicate username', r.status_code == 409)

    with c.session_transaction() as sess:
        sess['reg_step1_passed'] = {
            'username': 'user2', 'email': 'user2@test.com', 'password': '123456'
        }
    r = c.post('/auth/register/confirm', json={
        'username': 'user2', 'email': 'user2@test.com',
        'password': '123456', 'nickname': '用户二'
    })
    check('register user2', r.status_code == 200)

    with app.app_context():
        testuser_id = User.query.filter_by(username='testuser').first().id
        user2_id = User.query.filter_by(username='user2').first().id

    r = c.post('/auth/login', json={'login_id': 'testuser', 'password': 'wrong'})
    check('login wrong password', r.status_code == 401)

    r = c.post('/auth/login', json={'login_id': 'test@test.com', 'password': '123456'})
    check('login by email', r.status_code == 200)

    c.get('/auth/logout')

    r = c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})
    check('login by username', r.status_code == 200)

    r = c.get('/chat')
    check('chat page accessible', r.status_code == 200)

    section("Single Session (Kick-off)")
    # === Single Session (Kick-off) Test ===
    # Register kick user
    c.post('/auth/register/step1', json={'username': 'user_kick', 'email': 'kick@test.com', 'password': 'password'})
    with c.session_transaction() as sess:
        sess['reg_step1_passed'] = {'username': 'user_kick', 'email': 'kick@test.com', 'password': 'password'}
    res = c.post('/auth/register/confirm', json={'username': 'user_kick', 'email': 'kick@test.com', 'password': 'password', 'nickname': 'KickA'})
    check('user_kick register confirm status 200', res.status_code == 200)
    
    # Client A login
    res = c.post('/auth/login', json={'login_id': 'user_kick', 'password': 'password'})
    check('Client A login status 200', res.status_code == 200)
    check('Client A logged in', c.get('/chat').status_code == 200)

    # Client B login (same account)
    with app.test_client() as c_b:
        res = c_b.post('/auth/login', json={'login_id': 'user_kick', 'password': 'password'})
        check('Client B login status 200', res.status_code == 200)
        check('Client B logged in', c_b.get('/chat').status_code == 200)

    # Client A should now be redirected because its session_id in flask session 
    # no longer matches current_user.current_session_id in DB
    r = c.get('/chat', follow_redirects=False)
    check('Client A kicked off (302)', r.status_code == 302)

    # Verify Client A cannot perform API actions anymore
    r = c.post('/api/rooms', json={'name': 'Should Fail'})
    check('Kicked client blocked from API', r.status_code == 302 or r.status_code == 401)

    # Re-login for remaining tests
    c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})

    section("Room Management")
    # === Room CRUD ===
    r = c.post('/api/rooms', json={'name': '测试聊天室'})
    check('create room', r.status_code == 201)
    room_id = r.get_json()['id']

    r = c.post('/api/rooms', json={'name': '第二个'})
    check('duplicate room blocked', r.status_code == 403)

    r = c.get('/api/rooms')
    check('list rooms', r.status_code == 200 and len(r.get_json()) == 1)

    r = c.get(f'/api/rooms/{room_id}/members')
    check('initial members', r.status_code == 200 and len(r.get_json()) == 1)

    section("User Profile")
    # === Profile ===
    r = c.get('/api/users/me')
    check('get profile', r.status_code == 200)

    r = c.put('/api/users/me', json={'username': 'testuser_new'})
    check('update username', r.status_code == 200)

    r = c.post('/api/users/me/nickname', json={'nickname': '新昵称'})
    check('update nickname', r.status_code == 200)

    c.put('/api/users/me', json={'username': 'testuser'})  # revert

    section("Room Actions (Invite/Mute/Kick)")
    # === Invite / Mute / Kick ===
    r = c.post(f'/api/rooms/{room_id}/invite', json={'username': 'user2'})
    check('invite user', r.status_code == 200)

    r = c.get(f'/api/rooms/{room_id}/members')
    members = r.get_json()
    check('2 members after invite', len(members) == 2)
    user2_id = [m for m in members if m['username'] == 'user2'][0]['user_id']

    r = c.post(f'/api/rooms/{room_id}/mute/{user2_id}', json={'duration_minutes': 30})
    check('mute user', r.status_code == 200)

    r = c.post(f'/api/rooms/{room_id}/unmute/{user2_id}')
    check('unmute user', r.status_code == 200)

    r = c.post(f'/api/rooms/{room_id}/manager/{user2_id}')
    check('set manager', r.status_code == 200 and r.get_json().get('role') == 'manager')

    r = c.post(f'/api/rooms/{room_id}/manager/{user2_id}')
    check('unset manager', r.get_json().get('role') == 'member')

    r = c.post(f'/api/rooms/{room_id}/kick/{user2_id}')
    check('kick user', r.status_code == 200)

    r = c.get(f'/api/rooms/{room_id}/members')
    check('1 member after kick', len(r.get_json()) == 1)

    # === Unauthorized Actions ===
    # Login as user2 (not manager of room_id)
    c.get('/auth/logout')
    c.post('/auth/login', json={'login_id': 'user2', 'password': '123456'})
    
    r = c.post(f'/api/rooms/{room_id}/mute/{testuser_id}', json={'duration_minutes': 30})
    check('non-manager cannot mute', r.status_code == 403)

    r = c.post(f'/api/rooms/{room_id}/kick/{testuser_id}')
    check('non-manager cannot kick', r.status_code == 403)

    # Non-creator cannot dissolve room
    r = c.delete(f'/api/rooms/{room_id}')
    check('non-creator cannot dissolve room', r.status_code == 403)

    # Muted user speak permission service check
    with app.app_context():
        from models.room_member import RoomMember
        u2 = User.query.filter_by(username='user2').first()
        member = RoomMember.query.filter_by(room_id=room_id, user_id=u2.id).first()
        if not member:
            # Re-join if needed
            member = RoomMember(room_id=room_id, user_id=u2.id, role='member')
            db.session.add(member)
            db.session.commit()
        
        member.is_muted = True
        db.session.commit()
        check('muted user can_speak service returns False', not can_speak(u2.id, room_id))
        member.is_muted = False # reset
        db.session.commit()

    section("Messaging & Security")
    # === Messages ===
    # Re-login as testuser (creator)
    c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})
    r = c.get(f'/api/rooms/{room_id}/messages')
    check('get messages', r.status_code == 200)

    # === Leave (creator dissolves) ===
    r = c.post(f'/api/rooms/{room_id}/leave')
    check('creator leave dissolves', r.status_code == 200 and r.get_json().get('dissolved'))

    r = c.get('/api/rooms')
    check('no rooms after dissolve', len(r.get_json()) == 0)

    # === Nickname Validation ===
    nick_tests = [
        ('', False), ('   ', False), ('a' * 25, False),
        (' lead', False), ('trail ', False), ('dbl  space', False),
        ('正常昵称', True), ('test_name-1~', True), ('中文 En 123', True),
    ]
    for nick, expected in nick_tests:
        ok, _ = User.validate_nickname(nick)
        check(f'nickname "{nick}"={expected}', ok == expected)

    # === Upload magic bytes ===
    check('detect jpg', validate_image(b'\xff\xd8\xff\xe0') == 'jpg')
    check('detect png', validate_image(b'\x89PNG\r\n\x1a\n') == 'png')
    check('detect gif', validate_image(b'GIF89a') == 'gif')
    check('detect webp', validate_image(b'RIFF\x00\x00\x00\x00WEBP') == 'webp')
    check('reject invalid', validate_image(b'not an image') is None)

    # === Upload Security ===
    c.get('/auth/logout')
    r = c.get('/uploads/anyfile.png')
    check('unauth cannot access uploads', r.status_code in (302, 401))

    section("Admin API")
    # === Admin ===
    c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})
    with app.app_context():
        u = User.query.filter_by(username='testuser').first()
        u.is_admin = True
        db.session.commit()
        testuser_id = u.id
        u2_id = User.query.filter_by(username='user2').first().id

    r = c.get('/admin')
    check('admin page', r.status_code == 200)

    r = c.get('/admin/api/users')
    check('admin list users', r.status_code == 200 and r.get_json()['total'] == 3)

    r = c.get('/admin/api/users?search=user2')
    check('admin search user', r.get_json()['total'] == 1)

    r = c.post(f'/admin/api/users/{u2_id}/permission', json={'permission_type': 'ban_speak'})
    check('admin add permission', r.status_code == 201)
    perm_id = r.get_json()['id']

    r = c.get(f'/admin/api/users/{u2_id}/permissions')
    check('admin list perms', r.status_code == 200 and len(r.get_json()) == 1)

    r = c.delete(f'/admin/api/users/{u2_id}/permission/{perm_id}')
    check('admin remove perm', r.status_code == 200)

    r = c.post(f'/admin/api/users/{u2_id}/admin')
    check('admin toggle admin', r.status_code == 200)

    r = c.get('/admin/api/messages')
    check('admin messages', r.status_code == 200)

    r = c.get('/admin/api/rooms')
    check('admin rooms', r.status_code == 200)

    # === Permission service ===
    with app.app_context():
        check('user2 can create room', can_create_room(u2_id))

        perm = UserPermission(user_id=u2_id, permission_type='ban_create_room', issued_by=testuser_id)
        db.session.add(perm)
        db.session.commit()
        check('user2 banned from create', not can_create_room(u2_id))
        db.session.delete(perm)
        db.session.commit()

    # Delete user2
    r = c.delete(f'/admin/api/users/{u2_id}')
    check('admin delete user', r.status_code == 200)

    r = c.get('/admin/api/users')
    check('2 users after delete', r.get_json()['total'] == 2)

    section("Post-Cleanup & Unauth")
    # === Message Recall Logic (Timeout) ===
    with app.app_context():
        from datetime import datetime, timedelta
        # Create a message from 5 mins ago
        msg = Message(room_id=999, user_id=testuser_id, content="Old message") # room doesn't exist but FK is not enforced in memory sqlite usually or we don't care
        msg.created_at = datetime.utcnow() - timedelta(minutes=5)
        db.session.add(msg)
        db.session.commit()
        old_msg_id = msg.id
        
        # Manually test the logic used in on_recall_message
        now = datetime.utcnow()
        within_time = (now - msg.created_at) < timedelta(minutes=2)
        check('message from 5 mins ago is outside recall window', not within_time)

    r = c.delete(f'/admin/api/messages/{old_msg_id}')
    check('admin can delete old message', r.status_code == 200)

    # === Unauth access ===
    c.get('/auth/logout')

    r = c.get('/chat')
    check('unauth chat redirects', r.status_code in (302, 401))

    r = c.get('/admin')
    check('unauth admin redirects', r.status_code in (302, 401))

# === Summary ===
print(f"\n{'='*40}")
if errors:
    print(f"FAILED: {len(errors)}/{test_count} tests failed")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"ALL {test_count} TESTS PASSED")
