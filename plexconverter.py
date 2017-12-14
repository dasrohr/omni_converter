#!/usr/bin/env python
"""
simple HTTP server in embedded python

proccesses GET and uses HTTP Path as video URL to kick off youtube-dl
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
	# setting defaults
	global list_switch
        global verbose
	list_switch = 'no'
        verbose = ' '

	# function to enable downloads of a playlist
        def enable_playlist_dl():
            global list_switch
            list_switch = 'yes'

        def enable_verbose_dl():
	    global verbose
            print('VERBOSE AN')
            verbose = '--verbose'

        def invalid_option():
            print('invalid: ' + value)

        self._set_headers()
	passed = self.path	# catch the passed values
        passed = passed[1:]	# cutoff leading /
	values = passed.split('::')

	# get the url and remove from array
	url = values[0]
	values.remove(values[0])

	# build a list with options we can pass
        options = {'list' : enable_playlist_dl,
                   'debug' : enable_verbose_dl,
                  }

	# proccess the options
	for value in values:
	    # call function to set value & catch unknown options
            try:
                options[value]()
            except KeyError:
                invalid_option()

        print(values)
        print('url: ' + url + ' - playlist-switch : ' + list_switch + ' - debug: ' + verbose)
	subprocess.Popen(['youtube-dl', '--extract-audio', '--audio-format', 'mp3', '--output', '"%(title)s.%(ext)s"', '--' + list_switch + '-playlist', url])

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
