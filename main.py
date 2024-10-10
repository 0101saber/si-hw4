import os
import json
import socket
import threading
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import pathlib
from datetime import datetime

STORAGE_FOLDER = 'storage'
DATA_FILE = os.path.join(STORAGE_FOLDER, 'data.json')

WEB_PORT = 3000
SOCKET_PORT = 5000


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        if self.path == '/message.html':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data_parse = urllib.parse.unquote_plus(post_data)
            data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}

            send_message_to_socket(data_dict['username'], data_dict['message'])

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(self.path.lstrip('/'), 'rb') as file:
            self.wfile.write(file.read())


def send_message_to_socket(username, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', SOCKET_PORT)
    data = f'{username}:{message}'.encode('utf-8')
    sock.sendto(data, server_address)


def socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', SOCKET_PORT)
    sock.bind(server_address)

    while True:
        data, _ = sock.recvfrom(1024)
        process_data(data)


def process_data(data):
    data_str = data.decode('utf-8')
    username, message = data_str.split(':')

    timestamp = str(datetime.now())
    new_entry = {
        timestamp: {
            "username": username,
            "message": message
        }
    }

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            try:
                current_data = json.load(file)
            except json.JSONDecodeError:
                current_data = {}
    else:
        current_data = {}

    current_data.update(new_entry)

    with open(DATA_FILE, 'w') as file:
        json.dump(current_data, file, indent=4)


def run_http_server():
    server_address = ('', WEB_PORT)
    http = HTTPServer(server_address, HttpHandler)
    try:
        print(f"Serving HTTP on port {WEB_PORT}")
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


if __name__ == '__main__':
    socket_thread = threading.Thread(target=socket_server)
    socket_thread.start()

    run_http_server()
