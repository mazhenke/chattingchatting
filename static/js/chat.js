// State
let activeRoomId = null;
let myRooms = [];
let allRooms = [];
let socket = null;
let createRoomIconFile = null;
let onlineUserIds = new Set();

// Gradient colors for default avatars
const AVATAR_GRADIENTS = [
    'linear-gradient(135deg, #667eea, #764ba2)',
    'linear-gradient(135deg, #f093fb, #f5576c)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #a18cd1, #fbc2eb)',
    'linear-gradient(135deg, #fccb90, #d57eeb)',
    'linear-gradient(135deg, #e0c3fc, #8ec5fc)',
];

const ROOM_GRADIENTS = [
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #a18cd1, #fbc2eb)',
    'linear-gradient(135deg, #f093fb, #f5576c)',
    'linear-gradient(135deg, #fccb90, #d57eeb)',
];

function getAvatarGradient(id) {
    return AVATAR_GRADIENTS[id % AVATAR_GRADIENTS.length];
}

function getRoomGradient(id) {
    return ROOM_GRADIENTS[id % ROOM_GRADIENTS.length];
}

function renderAvatar(avatar, nickname, userId, size) {
    size = size || 38;
    if (avatar) {
        return `<div class="msg-avatar" style="width:${size}px;height:${size}px;"><img src="${escapeHtml(avatar)}" alt=""></div>`;
    }
    const ch = (nickname || '?')[0];
    const grad = getAvatarGradient(userId || 0);
    return `<div class="msg-avatar" style="width:${size}px;height:${size}px;"><div class="msg-avatar-letter" style="background:${grad};">${escapeHtml(ch)}</div></div>`;
}

function renderRoomIcon(icon, roomId, size) {
    size = size || 42;
    if (icon) {
        return `<img src="${escapeHtml(icon)}" style="width:${size}px;height:${size}px;border-radius:8px;object-fit:cover;">`;
    }
    const grad = getRoomGradient(roomId || 0);
    const icons = ['bi-chat-dots-fill', 'bi-stars', 'bi-lightning-fill', 'bi-fire', 'bi-heart-fill', 'bi-rocket-takeoff-fill'];
    const iconClass = icons[roomId % icons.length];
    return `<div style="width:${size}px;height:${size}px;border-radius:8px;background:${grad};display:flex;align-items:center;justify-content:center;color:#fff;font-size:${Math.floor(size*0.45)}px;"><i class="bi ${iconClass}"></i></div>`;
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    socket = io();
    setupSocket();
    loadLobby();
    loadMyRooms();
    setupInput();
    setupEmojiPicker();
    setupImageUpload();
    setupAvatarUpload();
    setupRoomIconUpload();
    setupCreateRoomIconUpload();
});

// ============ Socket Events ============

function setupSocket() {
    socket.on('connect', () => {
        myRooms.forEach(r => socket.emit('join_room', {room_id: r.id}));
    });

    socket.on('new_message', msg => {
        if (msg.room_id === activeRoomId) {
            appendMessage(msg);
            scrollToBottom();
        }
    });

    socket.on('message_history', data => {
        if (data.room_id === activeRoomId) {
            const container = document.getElementById('chat-messages');
            container.innerHTML = '';
            data.messages.forEach(m => appendMessage(m));
            scrollToBottom();
        }
    });

    socket.on('message_recalled', data => {
        const el = document.querySelector(`[data-msg-id="${data.message_id}"]`);
        if (el) {
            const body = el.querySelector('.msg-body');
            body.textContent = '消息已撤回';
            body.classList.add('msg-recalled');
            const actions = el.querySelector('.msg-actions');
            if (actions) actions.remove();
        }
    });

    socket.on('user_joined', data => {
        if (data.room_id === activeRoomId) {
            addSystemMessage(`${data.nickname} 加入了聊天室`);
            loadMembers(activeRoomId);
        }
    });

    socket.on('user_left', data => {
        if (data.room_id === activeRoomId) {
            addSystemMessage(`${data.nickname} 离开了聊天室`);
            loadMembers(activeRoomId);
        }
    });

    socket.on('user_kicked', data => {
        if (data.user_id === CURRENT_USER.id) {
            if (data.room_id === activeRoomId) {
                activeRoomId = null;
                resetChatArea();
            }
            loadMyRooms();
        } else if (data.room_id === activeRoomId) {
            loadMembers(activeRoomId);
        }
    });

    socket.on('user_muted', data => {
        if (data.room_id === activeRoomId) loadMembers(activeRoomId);
    });

    socket.on('room_dissolved', data => {
        if (data.room_id === activeRoomId) {
            activeRoomId = null;
            resetChatArea();
        }
        loadMyRooms();
        loadLobby();
    });

    socket.on('presence_change', data => {
        if (data.online) onlineUserIds.add(data.user_id);
        else onlineUserIds.delete(data.user_id);
        if (activeRoomId) updateMemberOnlineStatus();
    });

    socket.on('join_approved', () => { loadMyRooms(); loadLobby(); });
    socket.on('join_rejected', () => alert('您的加入申请被拒绝'));
    socket.on('join_request_received', data => {
        if (data.room_id === activeRoomId) loadJoinRequests(activeRoomId);
    });
    socket.on('error', data => alert(data.message));
}

// ============ Lobby ============

async function loadLobby() {
    const res = await fetch('/api/rooms');
    allRooms = await res.json();
    const container = document.getElementById('lobby-list');
    container.innerHTML = '';

    if (allRooms.length === 0) {
        container.innerHTML = `<div class="empty-state"><i class="bi bi-door-open"></i><p>暂无聊天室</p><small>点击"创建"开启第一个聊天室</small></div>`;
        return;
    }

    allRooms.forEach(room => {
        const isMember = myRooms.some(r => r.id === room.id);
        const card = document.createElement('div');
        card.className = 'room-card';
        card.innerHTML = `
            <div class="room-card-icon">${renderRoomIcon(room.icon, room.id, 42)}</div>
            <div class="room-card-info">
                <div class="room-card-name">${escapeHtml(room.name)}</div>
                <div class="room-card-meta">
                    <i class="bi bi-people-fill"></i> ${room.member_count}
                    <span>· ${escapeHtml(room.creator_name || '')}</span>
                </div>
                ${isMember ? '' : `<button class="btn btn-sm btn-outline-primary rounded-pill mt-1" onclick="event.stopPropagation(); requestJoin(${room.id})"><i class="bi bi-box-arrow-in-right me-1"></i>加入</button>`}
            </div>
        `;
        if (isMember) {
            card.onclick = () => switchRoom(room.id, room.name);
        }
        container.appendChild(card);
    });
}

async function requestJoin(roomId) {
    const res = await fetch(`/api/rooms/${roomId}/join`, {method: 'POST'});
    const data = await res.json();
    alert(data.success ? data.message : data.error);
}

// ============ My Rooms ============

async function loadMyRooms() {
    const res = await fetch('/api/rooms');
    const rooms = await res.json();
    allRooms = rooms;

    const memberPromises = rooms.map(async room => {
        const mRes = await fetch(`/api/rooms/${room.id}/members`);
        const members = await mRes.json();
        return members.some(m => m.user_id === CURRENT_USER.id) ? room : null;
    });

    myRooms = (await Promise.all(memberPromises)).filter(Boolean);
    renderMyRooms();
    loadLobby();
    myRooms.forEach(r => socket.emit('join_room', {room_id: r.id}));
}

function renderMyRooms() {
    const container = document.getElementById('my-rooms-list');
    container.innerHTML = '';

    if (myRooms.length === 0) {
        container.innerHTML = `<div class="empty-state small"><i class="bi bi-inbox"></i><p>未加入任何聊天室</p></div>`;
        return;
    }

    myRooms.forEach(room => {
        const isActive = room.id === activeRoomId;
        const item = document.createElement('div');
        item.className = `my-room-item ${isActive ? 'active' : ''}`;
        item.innerHTML = `
            <div class="my-room-item-icon">${renderRoomIcon(room.icon, room.id, 32)}</div>
            <div class="my-room-item-name">${escapeHtml(room.name)}</div>
        `;
        item.onclick = () => switchRoom(room.id, room.name);
        container.appendChild(item);
    });
}

function switchRoom(roomId, roomName) {
    if (activeRoomId === roomId) return;
    if (activeRoomId) socket.emit('leave_room', {room_id: activeRoomId});

    activeRoomId = roomId;

    // Update header
    const room = allRooms.find(r => r.id === roomId) || myRooms.find(r => r.id === roomId);
    document.getElementById('chat-room-name').textContent = roomName;
    const iconWrap = document.getElementById('chat-room-icon-wrap');
    const defaultIconWrap = document.getElementById('chat-room-default-icon-wrap');
    if (room && room.icon) {
        document.getElementById('chat-room-icon').src = room.icon;
        iconWrap.classList.remove('d-none');
        defaultIconWrap.classList.add('d-none');
    } else {
        iconWrap.classList.add('d-none');
        defaultIconWrap.classList.remove('d-none');
    }

    document.getElementById('chat-placeholder').remove?.() || null;
    const placeholder = document.getElementById('chat-placeholder');
    if (placeholder) placeholder.classList.add('d-none');
    document.getElementById('chat-input-bar').classList.remove('d-none');
    document.getElementById('chat-header-actions').classList.remove('d-none');
    document.getElementById('chat-messages').innerHTML = '';

    socket.emit('join_room', {room_id: roomId});
    loadMembers(roomId);
    renderMyRooms();
}

function resetChatArea() {
    document.getElementById('chat-room-name').textContent = '选择一个聊天室';
    document.getElementById('chat-room-icon-wrap').classList.add('d-none');
    document.getElementById('chat-room-default-icon-wrap').classList.add('d-none');
    document.getElementById('chat-input-bar').classList.add('d-none');
    document.getElementById('chat-header-actions').classList.add('d-none');
    const container = document.getElementById('chat-messages');
    container.innerHTML = `<div class="empty-state mt-5" id="chat-placeholder">
        <i class="bi bi-chat-square-text" style="font-size:4rem;color:#c5cae9;"></i>
        <p>选择或加入一个聊天室开始聊天</p>
        <small class="text-muted">在左侧大厅选择一个聊天室，或创建属于你的聊天室</small>
    </div>`;
    document.getElementById('member-list').innerHTML = '';
    document.getElementById('member-count').textContent = '0';
}

// ============ Members ============

async function loadMembers(roomId) {
    const [membersRes, onlineRes] = await Promise.all([
        fetch(`/api/rooms/${roomId}/members`),
        fetch(`/api/rooms/${roomId}/online`),
    ]);
    const members = await membersRes.json();
    const onlineData = await onlineRes.json();
    onlineUserIds = new Set(onlineData.online_ids || []);
    // Current user is always online
    onlineUserIds.add(CURRENT_USER.id);

    const container = document.getElementById('member-list');
    document.getElementById('member-count').textContent = members.length;
    container.innerHTML = '';

    const myMember = members.find(m => m.user_id === CURRENT_USER.id);
    const myRole = myMember ? myMember.role : null;
    const canManage = myRole === 'creator' || myRole === 'manager';

    // Sort: online first, then offline
    members.sort((a, b) => {
        const aOnline = onlineUserIds.has(a.user_id) ? 0 : 1;
        const bOnline = onlineUserIds.has(b.user_id) ? 0 : 1;
        if (aOnline !== bOnline) return aOnline - bOnline;
        // Within same status, sort by role: creator > manager > member
        const roleOrder = {creator: 0, manager: 1, member: 2};
        return (roleOrder[a.role] || 2) - (roleOrder[b.role] || 2);
    });

    members.forEach(m => {
        const isOnline = onlineUserIds.has(m.user_id);
        const item = document.createElement('div');
        item.className = `member-item${isOnline ? '' : ' member-offline'}`;
        item.dataset.userId = m.user_id;

        let roleHtml = '';
        if (m.role === 'creator') roleHtml = '<span class="member-role role-creator">创建者</span>';
        else if (m.role === 'manager') roleHtml = '<span class="member-role role-manager">管理</span>';

        let muteIcon = m.is_muted ? ' <i class="bi bi-mic-mute-fill text-danger" title="已禁言"></i>' : '';

        let actionsHtml = '';
        if (canManage && m.user_id !== CURRENT_USER.id && m.role !== 'creator') {
            actionsHtml = `<div class="member-actions">`;
            if (m.is_muted) {
                actionsHtml += `<button class="btn btn-outline-success btn-sm" onclick="unmuteMember(${m.user_id})" title="取消禁言"><i class="bi bi-mic-fill"></i></button>`;
            } else {
                actionsHtml += `<button class="btn btn-outline-warning btn-sm" onclick="showMuteModal(${m.user_id})" title="禁言"><i class="bi bi-mic-mute-fill"></i></button>`;
            }
            actionsHtml += `<button class="btn btn-outline-danger btn-sm" onclick="kickMember(${m.user_id})" title="踢出"><i class="bi bi-x-lg"></i></button>`;
            if (myRole === 'creator') {
                actionsHtml += `<button class="btn btn-outline-info btn-sm" onclick="toggleManager(${m.user_id})" title="${m.role === 'manager' ? '取消管理' : '设为管理'}"><i class="bi bi-shield-fill"></i></button>`;
            }
            actionsHtml += `</div>`;
        }

        // Avatar
        const avatarHtml = m.avatar
            ? `<div class="member-avatar"><img src="${escapeHtml(m.avatar)}" alt=""></div>`
            : `<div class="member-avatar"><div class="member-avatar-letter" style="background:${getAvatarGradient(m.user_id)};">${escapeHtml((m.nickname || '?')[0])}</div></div>`;

        // Online indicator dot
        const statusDot = `<span class="member-status-dot ${isOnline ? 'online' : 'offline'}" title="${isOnline ? '在线' : '离线'}"></span>`;

        item.innerHTML = `
            <div class="member-info">
                <div class="member-avatar-wrap">
                    ${avatarHtml}
                    ${statusDot}
                </div>
                <div class="member-name-wrap">
                    <span class="member-nickname">${escapeHtml(m.nickname)}${muteIcon}</span>
                    ${roleHtml}
                </div>
            </div>
            ${actionsHtml}
        `;
        container.appendChild(item);
    });
}

function updateMemberOnlineStatus() {
    document.querySelectorAll('.member-item[data-user-id]').forEach(item => {
        const userId = parseInt(item.dataset.userId);
        const isOnline = onlineUserIds.has(userId);
        item.classList.toggle('member-offline', !isOnline);
        const dot = item.querySelector('.member-status-dot');
        if (dot) {
            dot.className = `member-status-dot ${isOnline ? 'online' : 'offline'}`;
            dot.title = isOnline ? '在线' : '离线';
        }
    });
}

async function kickMember(userId) {
    if (!confirm('确定踢出该用户？')) return;
    const res = await fetch(`/api/rooms/${activeRoomId}/kick/${userId}`, {method: 'POST'});
    const data = await res.json();
    if (!data.success) alert(data.error);
    else loadMembers(activeRoomId);
}

function showMuteModal(userId) {
    document.getElementById('mute-user-id').value = userId;
    new bootstrap.Modal(document.getElementById('muteModal')).show();
}

async function confirmMute() {
    const userId = document.getElementById('mute-user-id').value;
    const durationStr = document.getElementById('mute-duration').value;
    const body = durationStr ? {duration_minutes: parseInt(durationStr)} : {};
    const res = await fetch(`/api/rooms/${activeRoomId}/mute/${userId}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!data.success) alert(data.error);
    bootstrap.Modal.getInstance(document.getElementById('muteModal')).hide();
    loadMembers(activeRoomId);
}

async function unmuteMember(userId) {
    const res = await fetch(`/api/rooms/${activeRoomId}/unmute/${userId}`, {method: 'POST'});
    const data = await res.json();
    if (!data.success) alert(data.error);
    else loadMembers(activeRoomId);
}

async function toggleManager(userId) {
    const res = await fetch(`/api/rooms/${activeRoomId}/manager/${userId}`, {method: 'POST'});
    const data = await res.json();
    if (!data.success) alert(data.error);
    else loadMembers(activeRoomId);
}

// ============ Messages ============

function appendMessage(msg) {
    const container = document.getElementById('chat-messages');
    const isSelf = msg.user_id === CURRENT_USER.id;
    const div = document.createElement('div');
    div.className = `msg-bubble ${isSelf ? 'msg-self' : ''}`;
    div.dataset.msgId = msg.id;

    const time = new Date(msg.created_at).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});

    let bodyContent;
    if (msg.is_recalled) {
        bodyContent = '<div class="msg-body msg-recalled">消息已撤回</div>';
    } else if (msg.msg_type === 'image') {
        bodyContent = `<div class="msg-body" style="padding:4px;"><img class="msg-image" src="${escapeHtml(msg.content)}" onclick="showImageLightbox('${escapeHtml(msg.content)}')" loading="lazy"></div>`;
    } else {
        bodyContent = `<div class="msg-body">${escapeHtml(msg.content)}</div>`;
    }

    let actionsHtml = '';
    if (!msg.is_recalled && isSelf) {
        actionsHtml = `<div class="msg-actions"><button class="btn btn-sm" onclick="recallMessage(${msg.id})" title="撤回"><i class="bi bi-arrow-counterclockwise"></i></button></div>`;
    }

    const avatarHtml = renderAvatar(msg.avatar, msg.nickname, msg.user_id, 38);

    div.innerHTML = `
        ${avatarHtml}
        <div class="msg-content-wrap">
            <div class="msg-nickname">${escapeHtml(msg.nickname || '')}</div>
            ${bodyContent}
            ${actionsHtml}
            <div class="msg-time">${time}</div>
        </div>
    `;
    container.appendChild(div);
}

function addSystemMessage(text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'msg-system';
    div.textContent = text;
    container.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

function recallMessage(msgId) {
    socket.emit('recall_message', {message_id: msgId});
}

function showImageLightbox(src) {
    document.getElementById('lightbox-image').src = src;
    new bootstrap.Modal(document.getElementById('imageModal')).show();
}

// Infinite scroll
document.addEventListener('DOMContentLoaded', () => {
    const msgContainer = document.getElementById('chat-messages');
    msgContainer.addEventListener('scroll', async () => {
        if (msgContainer.scrollTop === 0 && activeRoomId) {
            const firstMsg = msgContainer.querySelector('[data-msg-id]');
            if (!firstMsg) return;
            const beforeId = firstMsg.dataset.msgId;
            const prevHeight = msgContainer.scrollHeight;

            const res = await fetch(`/api/rooms/${activeRoomId}/messages?before=${beforeId}&limit=50`);
            const messages = await res.json();
            if (messages.length === 0) return;

            const fragment = document.createDocumentFragment();
            messages.forEach(m => {
                const isSelf = m.user_id === CURRENT_USER.id;
                const temp = document.createElement('div');
                temp.className = `msg-bubble ${isSelf ? 'msg-self' : ''}`;
                temp.dataset.msgId = m.id;
                const time = new Date(m.created_at).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
                let bodyContent;
                if (m.is_recalled) bodyContent = '<div class="msg-body msg-recalled">消息已撤回</div>';
                else if (m.msg_type === 'image') bodyContent = `<div class="msg-body" style="padding:4px;"><img class="msg-image" src="${escapeHtml(m.content)}" onclick="showImageLightbox('${escapeHtml(m.content)}')" loading="lazy"></div>`;
                else bodyContent = `<div class="msg-body">${escapeHtml(m.content)}</div>`;
                const avatarHtml = renderAvatar(m.avatar, m.nickname, m.user_id, 38);
                temp.innerHTML = `${avatarHtml}<div class="msg-content-wrap"><div class="msg-nickname">${escapeHtml(m.nickname || '')}</div>${bodyContent}<div class="msg-time">${time}</div></div>`;
                fragment.appendChild(temp);
            });

            msgContainer.insertBefore(fragment, msgContainer.firstChild);
            msgContainer.scrollTop = msgContainer.scrollHeight - prevHeight;
        }
    });
});

// ============ Input ============

function setupInput() {
    const input = document.getElementById('msg-input');
    const sendBtn = document.getElementById('btn-send');
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTextMessage(); }
    });
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
    sendBtn.addEventListener('click', sendTextMessage);
}

function sendTextMessage() {
    const input = document.getElementById('msg-input');
    const content = input.value.trim();
    if (!content || !activeRoomId) return;
    socket.emit('send_message', {room_id: activeRoomId, msg_type: 'text', content});
    input.value = '';
    input.style.height = 'auto';
}

// ============ Emoji ============

function setupEmojiPicker() {
    const container = document.getElementById('emoji-picker-container');
    const btn = document.getElementById('btn-emoji');
    const picker = document.createElement('emoji-picker');
    container.appendChild(picker);
    btn.addEventListener('click', () => container.classList.toggle('d-none'));
    picker.addEventListener('emoji-click', e => {
        document.getElementById('msg-input').value += e.detail.unicode;
        document.getElementById('msg-input').focus();
        container.classList.add('d-none');
    });
    document.addEventListener('click', e => {
        if (!container.contains(e.target) && e.target !== btn && !btn.contains(e.target))
            container.classList.add('d-none');
    });
}

// ============ Image Upload ============

function setupImageUpload() {
    const btn = document.getElementById('btn-image');
    const input = document.getElementById('image-input');
    btn.addEventListener('click', () => input.click());
    input.addEventListener('change', async () => {
        const file = input.files[0];
        if (!file || !activeRoomId) return;
        if (file.size > 10 * 1024 * 1024) { alert('图片大小不能超过10MB'); return; }
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/upload', {method: 'POST', body: formData});
        const data = await res.json();
        if (data.url) socket.emit('send_message', {room_id: activeRoomId, msg_type: 'image', content: data.url});
        else alert(data.error || '上传失败');
        input.value = '';
    });
}

// ============ Avatar Upload ============

function setupAvatarUpload() {
    document.getElementById('avatar-input').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) { alert('头像不能超过5MB'); return; }
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/users/me/avatar', {method: 'POST', body: formData});
        const data = await res.json();
        if (data.avatar) {
            CURRENT_USER.avatar = data.avatar;
            const img = document.getElementById('profile-avatar-img');
            img.src = data.avatar;
            img.classList.remove('d-none');
            document.getElementById('profile-avatar-default').classList.add('d-none');
        } else {
            alert(data.error || '上传失败');
        }
        e.target.value = '';
    });
}

// ============ Room Icon Upload ============

function setupRoomIconUpload() {
    document.getElementById('room-icon-input').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file || !activeRoomId) return;
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`/api/rooms/${activeRoomId}/icon`, {method: 'POST', body: formData});
        const data = await res.json();
        if (data.icon) {
            const preview = document.getElementById('settings-room-icon-preview');
            preview.innerHTML = `<img src="${data.icon}">`;
            loadMyRooms();
            loadLobby();
        } else {
            alert(data.error || '上传失败');
        }
        e.target.value = '';
    });
}

function setupCreateRoomIconUpload() {
    document.getElementById('create-room-icon-input').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        createRoomIconFile = file;
        const reader = new FileReader();
        reader.onload = (ev) => {
            document.getElementById('create-room-icon-preview').innerHTML = `<img src="${ev.target.result}">`;
        };
        reader.readAsDataURL(file);
    });
}

// ============ Room Management ============

function showCreateRoomModal() {
    document.getElementById('room-name-input').value = '';
    document.getElementById('create-room-error').classList.add('d-none');
    document.getElementById('create-room-icon-preview').innerHTML = '<i class="bi bi-chat-dots-fill"></i>';
    createRoomIconFile = null;
    new bootstrap.Modal(document.getElementById('createRoomModal')).show();
}

async function createRoom() {
    const name = document.getElementById('room-name-input').value.trim();
    const errDiv = document.getElementById('create-room-error');
    errDiv.classList.add('d-none');
    if (!name) { errDiv.textContent = '请输入聊天室名称'; errDiv.classList.remove('d-none'); return; }

    const res = await fetch('/api/rooms', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name})
    });
    const data = await res.json();
    if (data.error) { errDiv.textContent = data.error; errDiv.classList.remove('d-none'); return; }

    // Upload icon if selected
    if (createRoomIconFile && data.id) {
        const formData = new FormData();
        formData.append('file', createRoomIconFile);
        await fetch(`/api/rooms/${data.id}/icon`, {method: 'POST', body: formData});
    }

    bootstrap.Modal.getInstance(document.getElementById('createRoomModal')).hide();
    loadMyRooms();
    loadLobby();
}

async function showRoomSettings() {
    if (!activeRoomId) return;
    const res = await fetch(`/api/rooms/${activeRoomId}/members`);
    const members = await res.json();
    const me = members.find(m => m.user_id === CURRENT_USER.id);

    document.getElementById('btn-dissolve').classList.toggle('d-none', !me || me.role !== 'creator');
    document.getElementById('btn-change-room-icon').classList.toggle('d-none', !me || (me.role !== 'creator' && me.role !== 'manager'));

    // Show current room icon
    const room = allRooms.find(r => r.id === activeRoomId);
    const preview = document.getElementById('settings-room-icon-preview');
    if (room && room.icon) preview.innerHTML = `<img src="${escapeHtml(room.icon)}">`;
    else preview.innerHTML = '<i class="bi bi-chat-dots-fill"></i>';

    if (me && (me.role === 'creator' || me.role === 'manager')) loadJoinRequests(activeRoomId);
    else document.getElementById('join-requests-list').innerHTML = '<p class="text-muted small">无权查看申请</p>';

    document.getElementById('invite-error').classList.add('d-none');
    new bootstrap.Modal(document.getElementById('roomSettingsModal')).show();
}

async function loadJoinRequests(roomId) {
    const res = await fetch(`/api/rooms/${roomId}/requests`);
    const requests = await res.json();
    const container = document.getElementById('join-requests-list');
    if (requests.length === 0) { container.innerHTML = '<p class="text-muted small">无待处理申请</p>'; return; }
    container.innerHTML = '';
    requests.forEach(r => {
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center mb-2 p-2 rounded';
        div.style.background = 'var(--bg-secondary)';
        div.innerHTML = `
            <span><i class="bi bi-person-plus me-1"></i>${escapeHtml(r.nickname)} <small class="text-muted">(${escapeHtml(r.username)})</small></span>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-success rounded-pill" onclick="approveRequest(${roomId}, ${r.id})"><i class="bi bi-check-lg"></i></button>
                <button class="btn btn-danger rounded-pill" onclick="rejectRequest(${roomId}, ${r.id})"><i class="bi bi-x-lg"></i></button>
            </div>
        `;
        container.appendChild(div);
    });
}

async function approveRequest(roomId, reqId) {
    const res = await fetch(`/api/rooms/${roomId}/requests/${reqId}/approve`, {method: 'POST'});
    const data = await res.json();
    if (data.success) { loadJoinRequests(roomId); loadMembers(roomId); } else alert(data.error);
}

async function rejectRequest(roomId, reqId) {
    const res = await fetch(`/api/rooms/${roomId}/requests/${reqId}/reject`, {method: 'POST'});
    const data = await res.json();
    if (data.success) loadJoinRequests(roomId); else alert(data.error);
}

async function inviteUser() {
    const username = document.getElementById('invite-username').value.trim();
    const errDiv = document.getElementById('invite-error');
    errDiv.classList.add('d-none');
    if (!username) return;
    const res = await fetch(`/api/rooms/${activeRoomId}/invite`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username})
    });
    const data = await res.json();
    if (data.success) { document.getElementById('invite-username').value = ''; loadMembers(activeRoomId); alert('邀请成功'); }
    else { errDiv.textContent = data.error; errDiv.classList.remove('d-none'); }
}

async function leaveCurrentRoom() {
    if (!activeRoomId || !confirm('确定退出该聊天室？')) return;
    const res = await fetch(`/api/rooms/${activeRoomId}/leave`, {method: 'POST'});
    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('roomSettingsModal')).hide();
        activeRoomId = null; resetChatArea(); loadMyRooms(); loadLobby();
    } else alert(data.error);
}

async function dissolveRoom() {
    if (!activeRoomId || !confirm('确定解散该聊天室？此操作不可撤销！')) return;
    const res = await fetch(`/api/rooms/${activeRoomId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('roomSettingsModal')).hide();
        activeRoomId = null; resetChatArea(); loadMyRooms(); loadLobby();
    } else alert(data.error);
}

// ============ Profile ============

async function showProfileModal() {
    const res = await fetch('/api/users/me');
    const user = await res.json();
    document.getElementById('profile-username').value = user.username;
    document.getElementById('profile-email').value = user.email;
    document.getElementById('profile-nickname').value = user.nickname;
    document.getElementById('profile-password').value = '';
    document.getElementById('profile-error').classList.add('d-none');
    document.getElementById('profile-success').classList.add('d-none');

    // Avatar
    const img = document.getElementById('profile-avatar-img');
    const def = document.getElementById('profile-avatar-default');
    if (user.avatar) {
        img.src = user.avatar;
        img.classList.remove('d-none');
        def.classList.add('d-none');
    } else {
        img.classList.add('d-none');
        def.classList.remove('d-none');
        def.textContent = (user.nickname || '?')[0];
        def.style.background = getAvatarGradient(user.id);
    }

    new bootstrap.Modal(document.getElementById('profileModal')).show();
}

async function randomNickname() {
    const res = await fetch('/api/users/me/nickname', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({random: true})
    });
    const data = await res.json();
    if (data.nickname) document.getElementById('profile-nickname').value = data.nickname;
}

async function saveProfile() {
    const errDiv = document.getElementById('profile-error');
    const okDiv = document.getElementById('profile-success');
    errDiv.classList.add('d-none');
    okDiv.classList.add('d-none');

    const body = {};
    const username = document.getElementById('profile-username').value.trim();
    const email = document.getElementById('profile-email').value.trim();
    const password = document.getElementById('profile-password').value;
    const nickname = document.getElementById('profile-nickname').value.trim();
    if (username) body.username = username;
    if (email) body.email = email;
    if (password) body.password = password;

    let res = await fetch('/api/users/me', {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
    });
    let data = await res.json();
    if (data.error) { errDiv.textContent = data.error; errDiv.classList.remove('d-none'); return; }

    if (nickname) {
        res = await fetch('/api/users/me/nickname', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nickname})
        });
        data = await res.json();
        if (data.error) { errDiv.textContent = data.error; errDiv.classList.remove('d-none'); return; }
    }

    okDiv.textContent = '保存成功';
    okDiv.classList.remove('d-none');
    setTimeout(() => location.reload(), 1000);
}

async function deleteAccount() {
    if (!confirm('确定注销账号？此操作不可撤销！')) return;
    if (!confirm('再次确认：您的所有数据将被永久删除。')) return;
    const res = await fetch('/api/users/me', {method: 'DELETE'});
    const data = await res.json();
    if (data.success) window.location.href = '/auth/login';
    else alert(data.error);
}

// ============ Utility ============

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
