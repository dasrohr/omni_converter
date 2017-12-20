#!/usr/bin/env python
""" simple HTTP server in python
proccesses GET and uses HTTP Path and pass to a celery worker """
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from celery import chain
from omni_tasks import load, ytie

class Server(BaseHTTPRequestHandler):
    """ define the http-handlers """
    def _set_headers(self):
        """ build http-200 response """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """ define the GET handler """
        # building HTTP Header and extract path from it
        self._set_headers()
        seife = self.path	# passing the seife
        if seife:
            # start the celery chain
            chain(load.s([seife]), ytie.s()).apply_async()

def run(server_class=HTTPServer, handler_class=Server, port=8000):
    """ setting up the server parameter """
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd on port ' + str(port)
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
