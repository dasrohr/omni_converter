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
	global debug
	global dl
	debug = None
	dl = True

	# set youtube-dl default arguments
	args = ['youtube-dl', '--extract-audio', '--audio-format', 'mp3', '--output', '%(title)s.%(ext)s', '--no-playlist', '--quiet']

	# replace the argument to download a playlist (if there is any behind the url)
        def enable_playlist_dl():
	    args.remove('--no-playlist')
	    args.append('--yes-playlist')

        def enable_verbose_dl():
	    global debug
	    args.remove('--quiet')
	    args.append('--verbose')
	    debug = True

	def disable_dl():
	    global dl
	    dl = None

        def invalid_option():
            print('invalid option passed: ' + value)

	# building HTTP Header and extract path from it
	# contains '/url::arg:arg::...'
        self._set_headers()
	passed = self.path	# catch the passed values
        passed = passed[1:]	# cutoff leading /
	values = passed.split('::')

	# get the url and remove from array
	url = values[0]
	if url:
	    values.remove(values[0])
	 	   
	    # build a list with options we can pass and define the function to be executed
	    #  if the value is passed - { 'passed_value' : 'function name' }
	    options = {'list' : enable_playlist_dl,
	              'debug' : enable_verbose_dl,
		      'nodl' : disable_dl,
	             }
	    
	    # proccess the options
	    for value in values:
	        # call function to set value & catch unknown options
	        try:
	            options[value]()
	        except KeyError:
	            invalid_option()
	    
	    # append the url as the last argument to args
	    args.append(url)
	    
	    if debug == True:
	        print('catched url-options:')
	        print(values)
	        print('generated command:')
	        print(args)

	    # build an HTML Output
	    self.wfile.write("<html><head></head><body><p>got link: %s</p>" % url)

	    # if we have parameters passed through the url, print them
	    if len(values) > 0:
	        self.wfile.write("<p>Parameters: %s</p>" % values)

	    # if we want to debug, print all arguments send to the child-process
	    if debug:
	        self.wfile.write("<br><p>Debug:</p><p>%s</p>" % args)

	    self.wfile.write("</body></html>")
	    # HTML Output End

	    # KickOff Child-Process
	    if dl:
	        subprocess.Popen(args)
	else:
	    print('empty request')

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
