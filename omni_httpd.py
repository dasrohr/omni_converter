#!/usr/bin/env python
""" simple HTTP server in python
proccesses GET and uses HTTP Path and pass to a celery worker """
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import validators
from celery import chain
from omni_tasks import load, ytie

class Server(BaseHTTPRequestHandler):
    """ define the http-handlers """
    def _set_headers(self, is_url):
        """ build and send http response """
        # if url is valid, 200 OK
        if is_url:
            self.send_response(200)
        # else 400 Bad Request
        else:
            self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """ define the GET handler """
        # get the url-path
        seife = self.path
        print seifes
        # extract url and options from it
        values = seife[1:].split('::')
        # validate if url is a valid url
        is_url = True
        if not validators.url(values[0]):
            is_url = False

        # build the header
        self._set_headers(is_url)

        if is_url:
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
