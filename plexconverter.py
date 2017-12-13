#!/usr/bin/env python
"""
simple HTTP server in embedded python

proccesses GET and uses HTTP Path as video ID to kick off youtube-dl
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import subprocess

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
	passed_url = self.path
        dl_url = passed_url[1:]
	subprocess.Popen(['youtube-dl', '--extract-audio', '--audio-format', 'mp3', dl_url])

def run(server_class=HTTPServer, handler_class=S, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
