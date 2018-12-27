import logging
import SimpleHTTPServer
import SocketServer
import threading


class HTTPServer(threading.Thread):

    def __init__(self, port, event):
        threading.Thread.__init__(self)
        self.port = port
        self.event = event


    def run(self):
        http_server = SocketServer.TCPServer(("", self.port), QuietSimpleHTTPServer)
        logging.info("started http server on port %d", self.port)
        self.event.set()
        http_server.serve_forever()


class QuietSimpleHTTPServer(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass
