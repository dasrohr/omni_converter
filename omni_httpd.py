#!/usr/bin/env python
"""
simple HTTP server in python
proccesses GET and uses HTTP Path and pass to a celery worker
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
from omni_tasks import load, ytie
from celery import chain

class S(BaseHTTPRequestHandler):

  def _set_headers(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()

  def do_GET(self):
    # building HTTP Header and extract path from it
    self._set_headers()
    seife = self.path	# passing the seife
    if seife:
      # start the celery chain
      chain(load.s([seife]), ytie.s()).apply_async()

def run(server_class=HTTPServer, handler_class=S, port=8000):
  server_address = ('', port)
  httpd = server_class(server_address, handler_class)
  print('Starting httpd on port ' + port)
  httpd.serve_forever()

if __name__ == "__main__":
  from sys import argv
  if len(argv) == 2:
    run(port=int(argv[1]))
  else:
    run()