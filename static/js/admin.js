// ============ Users ============

let usersPage = 1;
let messagesPage = 1;

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();

    // Tab event listeners to load data on tab switch
    document.querySelector('[data-bs-target="#tab-rooms"]').addEventListener('shown.bs.tab', loadRooms);
    document.querySelector('[data-bs-target="#tab-messages"]').addEventListener('shown.bs.tab', () => loadMessages());

    // Show/hide room ID input based on permission type
    document.getElementById('perm-type').addEventListener('change', e => {
        document.getElementById('perm-room-id').classList.toggle('d-none', e.target.value !== 'ban_room');
    });
});

async function loadUsers(page) {
    usersPage = page || 1;
    const search = document.getElementById('user-search').value.trim();
    const params = new URLSearchParams({page: usersPage, per_page: 20});
    if (search) params.set('search', search);

    const res = await fetch(`/admin/api/users?${params}`);
    const data = await res.json();
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '';

    data.users.forEach(u => {
        const tr = document.createElement('tr');
        const time = u.created_at ? new Date(u.created_at).toLocaleDateString('zh-CN') : '';
        tr.innerHTML = `
            <td>${u.id}</td>
            <td>${esc(u.username)}</td>
            <td>${esc(u.nickname)}</td>
            <td>${esc(u.email)}</td>
            <td>${u.is_admin ? '<span class="badge bg-danger">是</span>' : '否'}</td>
            <td>${time}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info" onclick="toggleAdmin(${u.id})">${u.is_admin ? '取消管理' : '设为管理'}</button>
                    <button class="btn btn-outline-warning" onclick="showPermModal(${u.id})">权限</button>
                    <button class="btn btn-outline-secondary" onclick="showUserPerms(${u.id})">查看权限</button>
                    <button class="btn btn-outline-danger" onclick="deleteUser(${u.id})">删除</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });

    renderPagination('users-pagination', data.pages, usersPage, loadUsers);
}

function searchUsers() {
    loadUsers(1);
}

async function deleteUser(userId) {
    if (!confirm('确定删除该用户？')) return;
    const res = await fetch(`/admin/api/users/${userId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) loadUsers(usersPage);
    else alert(data.error);
}

async function toggleAdmin(userId) {
    const res = await fetch(`/admin/api/users/${userId}/admin`, {method: 'POST'});
    const data = await res.json();
    if (data.success !== undefined) loadUsers(usersPage);
    else alert(data.error);
}

function showPermModal(userId) {
    document.getElementById('perm-user-id').value = userId;
    document.getElementById('perm-type').value = 'ban_all_rooms';
    document.getElementById('perm-room-id').classList.add('d-none');
    new bootstrap.Modal(document.getElementById('permModal')).show();
}

async function addPermission() {
    const userId = document.getElementById('perm-user-id').value;
    const permType = document.getElementById('perm-type').value;
    const roomId = document.getElementById('perm-room-id').value;

    const body = {permission_type: permType};
    if (permType === 'ban_room' && roomId) body.room_id = parseInt(roomId);

    const res = await fetch(`/admin/api/users/${userId}/permission`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const data = await res.json();

    if (data.error) {
        alert(data.error);
    } else {
        bootstrap.Modal.getInstance(document.getElementById('permModal')).hide();
        alert('权限已添加');
    }
}

async function showUserPerms(userId) {
    document.getElementById('perms-list-user-id').value = userId;
    const res = await fetch(`/admin/api/users/${userId}/permissions`);
    const perms = await res.json();
    const container = document.getElementById('perms-list-container');

    if (perms.length === 0) {
        container.innerHTML = '<p class="text-muted">无权限记录</p>';
    } else {
        const permLabels = {
            'ban_all_rooms': '禁止进入所有聊天室',
            'ban_create_room': '禁止创建聊天室',
            'ban_speak': '禁止发言',
            'ban_room': '禁止进入聊天室',
            'kick_room': '踢出聊天室',
        };
        container.innerHTML = '';
        perms.forEach(p => {
            const div = document.createElement('div');
            div.className = 'd-flex justify-content-between align-items-center mb-2';
            let label = permLabels[p.permission_type] || p.permission_type;
            if (p.room_id) label += ` #${p.room_id}`;
            div.innerHTML = `
                <span>${label}</span>
                <button class="btn btn-sm btn-outline-danger" onclick="removePerm(${userId}, ${p.id})">移除</button>
            `;
            container.appendChild(div);
        });
    }

    new bootstrap.Modal(document.getElementById('userPermsModal')).show();
}

async function removePerm(userId, permId) {
    const res = await fetch(`/admin/api/users/${userId}/permission/${permId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) showUserPerms(userId);
    else alert(data.error);
}

// ============ Rooms ============

async function loadRooms() {
    const res = await fetch('/admin/api/rooms');
    const rooms = await res.json();
    const tbody = document.getElementById('rooms-tbody');
    tbody.innerHTML = '';

    rooms.forEach(r => {
        const tr = document.createElement('tr');
        const time = r.created_at ? new Date(r.created_at).toLocaleDateString('zh-CN') : '';
        tr.innerHTML = `
            <td>${r.id}</td>
            <td>${esc(r.name)}</td>
            <td>${esc(r.creator_name || '')} (ID:${r.creator_id})</td>
            <td>${r.member_count}</td>
            <td>${time}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info" onclick="viewRoomMembers(${r.id})">成员</button>
                    <button class="btn btn-outline-danger" onclick="forceDissolve(${r.id})">解散</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function forceDissolve(roomId) {
    if (!confirm('确定强制解散该聊天室？')) return;
    const res = await fetch(`/admin/api/rooms/${roomId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) loadRooms();
    else alert(data.error);
}

async function viewRoomMembers(roomId) {
    const res = await fetch(`/admin/api/rooms/${roomId}/members`);
    const members = await res.json();
    const container = document.getElementById('room-members-container');

    if (members.length === 0) {
        container.innerHTML = '<p class="text-muted">无成员</p>';
    } else {
        container.innerHTML = '<table class="table table-sm"><thead><tr><th>用户</th><th>昵称</th><th>角色</th><th>禁言</th></tr></thead><tbody>';
        members.forEach(m => {
            container.innerHTML += `<tr>
                <td>${esc(m.username || '')}</td>
                <td>${esc(m.nickname || '')}</td>
                <td>${m.role}</td>
                <td>${m.is_muted ? '是' : '否'}</td>
            </tr>`;
        });
        container.innerHTML += '</tbody></table>';
    }

    new bootstrap.Modal(document.getElementById('roomMembersModal')).show();
}

// ============ Messages ============

async function loadMessages(page) {
    messagesPage = page || 1;
    const params = new URLSearchParams({page: messagesPage, per_page: 50});

    const roomId = document.getElementById('msg-room-filter').value;
    const userId = document.getElementById('msg-user-filter').value;
    const keyword = document.getElementById('msg-keyword-filter').value.trim();

    if (roomId) params.set('room_id', roomId);
    if (userId) params.set('user_id', userId);
    if (keyword) params.set('keyword', keyword);

    const res = await fetch(`/admin/api/messages?${params}`);
    const data = await res.json();
    const tbody = document.getElementById('messages-tbody');
    tbody.innerHTML = '';

    data.messages.forEach(m => {
        const tr = document.createElement('tr');
        const time = m.created_at ? new Date(m.created_at).toLocaleString('zh-CN') : '';
        let contentDisplay = m.is_recalled ? '<i>已撤回</i>' : '';
        if (!m.is_recalled) {
            if (m.msg_type === 'image') {
                contentDisplay = `<img src="${esc(m.content)}" style="max-height:60px;max-width:100px;">`;
            } else {
                contentDisplay = esc(m.content).substring(0, 100);
            }
        }
        tr.innerHTML = `
            <td>${m.id}</td>
            <td>${m.room_id}</td>
            <td>${esc(m.nickname || '')} (${m.user_id})</td>
            <td>${m.msg_type}</td>
            <td>${contentDisplay}</td>
            <td>${time}</td>
            <td><button class="btn btn-sm btn-outline-danger" onclick="deleteMessage(${m.id})">删除</button></td>
        `;
        tbody.appendChild(tr);
    });

    renderPagination('messages-pagination', data.pages, messagesPage, loadMessages);
}

function searchMessages() {
    loadMessages(1);
}

async function deleteMessage(msgId) {
    if (!confirm('确定删除该消息？')) return;
    const res = await fetch(`/admin/api/messages/${msgId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) loadMessages(messagesPage);
    else alert(data.error);
}

// ============ Utility ============

function renderPagination(containerId, totalPages, currentPage, loadFn) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (totalPages <= 1) return;

    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', e => {
            e.preventDefault();
            loadFn(i);
        });
        container.appendChild(li);
    }
}

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
