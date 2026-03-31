const step1Div = document.getElementById('step1');
const step2Div = document.getElementById('step2');
const successDiv = document.getElementById('step-success');
const loginLink = document.getElementById('login-link');

// Step 1 -> Step 2
document.getElementById('btn-step1').addEventListener('click', async () => {
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const password2 = document.getElementById('password2').value;
    const errDiv = document.getElementById('step1-error');
    errDiv.classList.add('d-none');

    if (password !== password2) {
        errDiv.textContent = '两次输入的密码不一致';
        errDiv.classList.remove('d-none');
        return;
    }

    const res = await fetch('/auth/register/step1', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, email, password})
    });
    const data = await res.json();

    if (data.valid) {
        step1Div.classList.add('d-none');
        step2Div.classList.remove('d-none');
        // Update step indicator
        document.getElementById('step-dot-1').classList.remove('active');
        document.getElementById('step-dot-2').classList.add('active');
        document.getElementById('step-line').classList.add('active');
        // Auto-generate a nickname
        generateNickname();
    } else {
        errDiv.textContent = data.error;
        errDiv.classList.remove('d-none');
    }
});

// Back to step 1
document.getElementById('btn-back').addEventListener('click', () => {
    step2Div.classList.add('d-none');
    step1Div.classList.remove('d-none');
    document.getElementById('step-dot-2').classList.remove('active');
    document.getElementById('step-dot-1').classList.add('active');
    document.getElementById('step-line').classList.remove('active');
});

// Dice button - random nickname
document.getElementById('btn-dice').addEventListener('click', generateNickname);

async function generateNickname() {
    const btn = document.getElementById('btn-dice');
    btn.disabled = true;
    try {
        const res = await fetch('/auth/register/step2', {method: 'POST'});
        const data = await res.json();
        document.getElementById('nickname').value = data.nickname;
    } catch (e) {
        console.error('Failed to generate nickname:', e);
    }
    btn.disabled = false;
}

// Confirm registration
document.getElementById('btn-confirm').addEventListener('click', async () => {
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const nickname = document.getElementById('nickname').value.trim();
    const errDiv = document.getElementById('step2-error');
    errDiv.classList.add('d-none');

    if (!nickname) {
        errDiv.textContent = '昵称不能为空';
        errDiv.classList.remove('d-none');
        return;
    }

    const res = await fetch('/auth/register/confirm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, email, password, nickname})
    });
    const data = await res.json();

    if (data.success) {
        step2Div.classList.add('d-none');
        loginLink.classList.add('d-none');
        document.getElementById('step-indicator').classList.add('d-none');
        successDiv.classList.remove('d-none');
    } else {
        errDiv.textContent = data.error;
        errDiv.classList.remove('d-none');
    }
});
