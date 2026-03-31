# GEMINI.md

## Project Overview

**Anonymous Chat** is a real-time web-based chat application built with Flask and Socket.IO. It features a server-side web application and a lightweight desktop client wrapper using `pywebview`.

### Key Technologies
- **Backend:** Flask 3.0.3, Flask-SocketIO (for real-time events), Flask-SQLAlchemy (with SQLite by default), Flask-Login (session management).
- **Frontend:** HTML/CSS/JS (Vanilla JS for chat logic), Jinja2 templates.
- **Desktop Client:** Python with `pywebview` and `PyInstaller` for packaging.
- **Database:** SQLite (default `chat.db` in `instance/` folder).

### Architecture
- `app.py`: Application entry point and factory.
- `models/`: Database models (User, ChatRoom, Message, etc.).
- `routes/`: Flask Blueprints for auth, chat, room management, and admin.
- `sockets/`: Socket.IO event handlers for real-time communication.
- `services/`: Business logic like nickname generation and permission checks.
- `static/` & `templates/`: Frontend assets and HTML templates.
- `desktop.py`: Desktop client that connects to the server.

---

## Building and Running

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Server Setup
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Initialize Database:**
   The database is automatically created on first run via `db.create_all()` in `app.py`.
3. **Create Admin User:**
   ```bash
   python app.py --create-admin
   ```
4. **Run Server:**
   ```bash
   python app.py
   ```
   The server will run on `http://0.0.0.0:5000` with debug mode enabled.

### Desktop Client Setup
1. **Install dependencies:**
   ```bash
   pip install -r requirements-desktop.txt
   ```
2. **Run Client:**
   ```bash
   python desktop.py
   ```
   *Note: On first run or with `--reconfigure`, it will prompt for the server URL (e.g., `http://localhost:5000`).*
3. **Build Binary:**
   - **Linux:** `./build_linux.sh`
   - **Windows:** `build_windows.bat`

### Testing
Run the comprehensive test suite:
```bash
python test_all.py
```
This script uses an in-memory SQLite database (`DATABASE_URL='sqlite://'`) to avoid modifying production data. It covers authentication, room CRUD, user profile, administrative actions, and permission services.

---

## Development Conventions

- **Real-time:** Use Socket.IO events for all messaging and room state changes. Handlers are located in `sockets/`.
- **Modularity:** Keep routes organized within `routes/` using Blueprints.
- **Models:** Add new database entities to `models/` and ensure they are imported in `models/__init__.py`.
- **Static Assets:** Client-side chat logic is primarily in `static/js/chat.js`.
- **Uploads:** Files are stored in the `uploads/` directory (configured in `config.py`).
- **Nicknames:** The app uses an external service (`https://www.qmsjmfb.com/erciyuan.php`) to generate random nicknames for users.
