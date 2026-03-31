"""Desktop client for Anonymous Chat - connects to a remote server via pywebview."""

import json
import os
import sys

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.anonchat_config.json')


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


def get_server_url():
    config = load_config()
    url = config.get('server_url', '')

    if url and '--reconfigure' not in sys.argv:
        return url

    # Prompt for server URL
    try:
        import webview

        result = {'url': ''}

        def on_shown(window):
            pass

        def ask_url():
            win = webview.create_window(
                'Anonymous Chat - 配置',
                html='''
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: sans-serif; padding: 40px; text-align: center; background: #f8f9fa; }
                        input { width: 300px; padding: 8px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
                        button { padding: 8px 24px; font-size: 16px; background: #0d6efd; color: white;
                                 border: none; border-radius: 4px; cursor: pointer; margin-top: 12px; }
                        button:hover { background: #0b5ed7; }
                    </style>
                </head>
                <body>
                    <h2>匿名聊天室</h2>
                    <p>请输入服务器地址：</p>
                    <input type="text" id="url" placeholder="http://192.168.1.100:5000" value="">
                    <br>
                    <button onclick="pywebview.api.set_url(document.getElementById('url').value)">连接</button>
                </body>
                </html>
                ''',
                width=450,
                height=280,
                resizable=False,
            )
            return win

        class Api:
            def set_url(self, url):
                result['url'] = url.strip().rstrip('/')
                config['server_url'] = result['url']
                save_config(config)
                # Close config window and open main window
                for w in webview.windows:
                    w.destroy()

        api = Api()
        win = webview.create_window(
            'Anonymous Chat - 配置',
            html='''
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { font-family: sans-serif; padding: 40px; text-align: center; background: #f8f9fa; }
                    input { width: 300px; padding: 8px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
                    button { padding: 8px 24px; font-size: 16px; background: #0d6efd; color: white;
                             border: none; border-radius: 4px; cursor: pointer; margin-top: 12px; }
                    button:hover { background: #0b5ed7; }
                </style>
            </head>
            <body>
                <h2>匿名聊天室</h2>
                <p>请输入服务器地址：</p>
                <input type="text" id="url" placeholder="http://192.168.1.100:5000">
                <br>
                <button onclick="pywebview.api.set_url(document.getElementById('url').value)">连接</button>
            </body>
            </html>
            ''',
            js_api=api,
            width=450,
            height=280,
            resizable=False,
        )
        webview.start()
        return result['url']

    except ImportError:
        # Fallback to terminal input
        url = input('请输入服务器地址 (例: http://192.168.1.100:5000): ').strip().rstrip('/')
        config['server_url'] = url
        save_config(config)
        return url


def main():
    import webview

    server_url = get_server_url()
    if not server_url:
        print('未配置服务器地址，退出。')
        sys.exit(1)

    webview.create_window(
        '匿名聊天室',
        f'{server_url}/auth/login',
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == '__main__':
    main()
