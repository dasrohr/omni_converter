#!/usr/bin/env python
"""
Very simple HTTP server in python.
Usage::
    ./dummy-web-server.py [<port>]
Send a GET request::
    curl http://localhost
Send a HEAD request::
    curl -I http://localhost
Send a POST request::
    curl -d "foo=bar&bin=baz" http://localhost
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
	videoid = self.path
	video_url = 'https://youtu.be/' + videoid
	subprocess.call(['youtube-dl', '-x', video_url])

#    def do_HEAD(self):
#        self._set_headers()
#        
#    def do_POST(self):
#
#        
#        request_path = self.path
#        
#        print("\n----- Request Start ----->\n")
#        #print(request_path)
#        
#        request_headers = self.headers
#        content_length = request_headers.getheaders('content-length')
#        length = int(content_length[0]) if content_length else 0
#        
#        #print(request_headers)
#        print(self.rfile.read(length))
#        print("<----- Request End -----\n")
#        
#	self.send_response(200)
#
#        # Doesn't do anything with posted data
#        #self._see_headers()
#        #self.wfile.write("<html><body><h1>POST!</h1></body></html>")
        
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
