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
from models.permission import UserPermission
from routes.upload import validate_image
from services.permissions import can_create_room, can_speak, can_enter_rooms

def check(name, condition):
    global test_count
    test_count += 1
    if not condition:
        errors.append(name)
        print(f"  FAIL: {name}")


with app.test_client() as c:
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

    r = c.post('/auth/login', json={'login_id': 'testuser', 'password': 'wrong'})
    check('login wrong password', r.status_code == 401)

    r = c.post('/auth/login', json={'login_id': 'test@test.com', 'password': '123456'})
    check('login by email', r.status_code == 200)

    c.get('/auth/logout')

    r = c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})
    check('login by username', r.status_code == 200)

    r = c.get('/chat')
    check('chat page accessible', r.status_code == 200)

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

    # === Profile ===
    r = c.get('/api/users/me')
    check('get profile', r.status_code == 200)

    r = c.put('/api/users/me', json={'username': 'testuser_new'})
    check('update username', r.status_code == 200)

    r = c.post('/api/users/me/nickname', json={'nickname': '新昵称'})
    check('update nickname', r.status_code == 200)

    c.put('/api/users/me', json={'username': 'testuser'})  # revert

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

    # === Messages ===
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

    # === Admin ===
    with app.app_context():
        u = User.query.filter_by(username='testuser').first()
        u.is_admin = True
        db.session.commit()
        testuser_id = u.id

    c.post('/auth/login', json={'login_id': 'testuser', 'password': '123456'})

    r = c.get('/admin')
    check('admin page', r.status_code == 200)

    r = c.get('/admin/api/users')
    check('admin list users', r.status_code == 200 and r.get_json()['total'] == 2)

    r = c.get('/admin/api/users?search=user2')
    check('admin search user', r.get_json()['total'] == 1)

    r = c.post(f'/admin/api/users/{user2_id}/permission', json={'permission_type': 'ban_speak'})
    check('admin add permission', r.status_code == 201)
    perm_id = r.get_json()['id']

    r = c.get(f'/admin/api/users/{user2_id}/permissions')
    check('admin list perms', r.status_code == 200 and len(r.get_json()) == 1)

    r = c.delete(f'/admin/api/users/{user2_id}/permission/{perm_id}')
    check('admin remove perm', r.status_code == 200)

    r = c.post(f'/admin/api/users/{user2_id}/admin')
    check('admin toggle admin', r.status_code == 200)

    r = c.get('/admin/api/messages')
    check('admin messages', r.status_code == 200)

    r = c.get('/admin/api/rooms')
    check('admin rooms', r.status_code == 200)

    # === Permission service ===
    with app.app_context():
        check('user2 can create room', can_create_room(user2_id))

        perm = UserPermission(user_id=user2_id, permission_type='ban_create_room', issued_by=testuser_id)
        db.session.add(perm)
        db.session.commit()
        check('user2 banned from create', not can_create_room(user2_id))
        db.session.delete(perm)
        db.session.commit()

    # Delete user2
    r = c.delete(f'/admin/api/users/{user2_id}')
    check('admin delete user', r.status_code == 200)

    r = c.get('/admin/api/users')
    check('1 user after delete', r.get_json()['total'] == 1)

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
