# 匿名聊天室 (Anonymous Chat)

这是一个基于 Flask 和 Socket.IO 开发的实时匿名聊天系统。项目包含功能完善的后端服务器、Web 前端以及一个基于 `pywebview` 的轻量级桌面客户端。

## 功能特性

- **实时通信**：基于 Socket.IO 实现低延迟的消息推送。
- **聊天室管理**：支持创建、加入、退出和解散聊天室。
- **权限控制**：
    - **创建者**：拥有最高权限，可解散房间、任命/撤职管理员。
    - **管理员**：可邀请用户、禁言用户、踢出成员。
    - **普通成员**：可参与聊天、申请加入。
- **管理后台**：管理员可进行用户禁言（全局）、封禁、删除消息等操作。
- **匿名性**：系统自动从外部 API 获取随机昵称，保护用户隐私。
- **图片上传**：支持发送图片消息，并进行魔数（Magic Bytes）校验以确保安全。
- **消息撤回**：支持 2 分钟内撤回消息，管理员可随时撤回。
- **桌面客户端**：提供跨平台的桌面包装版本。

## 技术栈

- **后端**：Flask 3.0.3, Flask-SocketIO, Flask-SQLAlchemy, Flask-Login
- **数据库**：SQLite (默认)
- **前端**：原生 JavaScript, HTML, CSS (Jinja2 模板)
- **桌面端**：Python, pywebview, PyInstaller

## 快速开始

### 1. 环境准备

确保您的系统中已安装 Python 3.8 或更高版本。

### 2. 安装依赖

建议在虚拟环境中运行：

```bash
# 安装服务端依赖
pip install -r requirements.txt

# 如果需要运行或打包桌面客户端，请安装
pip install -r requirements-desktop.txt
```

### 3. 初始化与运行

1. **创建管理员账号**：
   ```bash
   python app.py --create-admin
   ```
   按照提示输入用户名、邮箱、密码和昵称。

2. **启动服务端**：
   ```bash
   python app.py
   ```
   服务器默认运行在 `http://127.0.0.1:5000`。

3. **运行桌面客户端**（可选）：
   ```bash
   python desktop.py
   ```
   首次运行会提示输入服务器地址，输入 `http://127.0.0.1:5000` 即可。

### 4. 运行测试

系统包含完善的自动化测试套件，覆盖了权限、认证、聊天逻辑等：

```bash
python test_all.py
```

## 项目结构

```text
├── app.py              # 应用入口，包含工厂函数和管理命令行
├── config.py           # 配置文件
├── models/             # 数据库模型 (User, Message, Room 等)
├── routes/             # 路由蓝图 (Auth, Chat, Admin, Upload 等)
├── sockets/            # Socket.IO 事件处理逻辑
├── services/           # 业务逻辑服务 (权限校验、昵称生成)
├── static/             # 静态资源 (JS, CSS)
├── templates/          # HTML 模板
├── test_all.py         # 综合测试脚本
└── desktop.py          # 桌面客户端逻辑
```

## 构建桌面端

- **Linux**: 执行 `./build_linux.sh`
- **Windows**: 执行 `build_windows.bat`

构建完成后，二进制文件将生成在 `dist/` 目录下。

## 安全说明

- **密码存储**：目前使用 SHA-256 哈希（建议在生产环境升级为 Argon2 或 BCrypt）。
- **文件上传**：严格校验文件大小及图片格式。
- **访问控制**：上传文件访问需登录授权，敏感操作均有后端权限检查。
