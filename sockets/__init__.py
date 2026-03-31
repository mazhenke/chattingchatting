def register_socket_handlers(socketio):
    from sockets import chat_events  # noqa: F401
    from sockets import room_events  # noqa: F401
