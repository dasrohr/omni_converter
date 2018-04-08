#!/usr/bin/env python
""" simple HTTP server in python
proccesses GET and uses HTTP Path and pass to a celery worker """
from validators import url as validate_url
from celery import chain
from omni_tasks import load, ytie

from bottle import template, get, post, request, run, error, abort, static_file, auth_basic, route

def check(user, pw):
    if user == 'junge' and pw == 'bier':
        return(True)
    return(False)

@get('/') # or @route('/login')
@auth_basic(check)
def login():
    return static_file('form.html', root='.')

@post('/') # or @route('/login', method='POST')
@auth_basic(check)
def do_login():
    url = request.forms.get('url')
    vid = request.forms.get('vid')
    pid = request.forms.get('pid')
    target = request.forms.get('target')
    debug = request.forms.get('debug')

    if url and not validate_url(url):
        abort(400, 'url invalid - ' + url)

    if not url and not vid and not pid:
        abort(400, 'You entered nothing!? - DoeDoeDoe')

    return template("You entered: url: {{u}} - video id: {{vid}} - playlist id: {{pid}}</br>We are loading a {{target}}</br>debug? {{debug}}", u=url, vid=vid, pid=pid, target=target, debug=debug)

@route('/src/<filename>')
@auth_basic(check)
def server_static(filename):
    return static_file(filename, root='./src/')

run()

###########################
#
#class Server(BaseHTTPRequestHandler):
#    """ define the http-handlers """
##    def _set_headers(self, is_url):
##        """ build and send http response """
##        # if url is valid, 200 OK
##        if is_url:
##            self.send_response(200)
##        # else 400 Bad Request
##        else:
##            self.send_response(400)
##        self.send_header('Content-type', 'text/html')
##        self.end_headers()
#
##    def do_POST(self):
##        length = int(self.headers.getheader('content-length'))
##        field_data = self.rfile.read(length)
##        fields = urlparse.parse_qs(field_data)
##        print length
##        print field_data
##        print fields
#
#    def do_GET(self):
#        """ define the GET handler """
#        print(parse_qs(urlparse(self.path).query))
#        print(urlparse(self.path))
#        #field_data = self.rfile.read(length)
#        #fields = urlparse.parse_qs(field_data)
#        #print field_data
#        #print fields
#        # get the url-path
#        seife = self.path
#        # extract url and options from it
#        values = seife[1:].split('::')
#        # validate if url is a valid url
#        is_url = validators.url(values[0])
#
#        app = Bottle()
#
#        app.route()
##        self._set_headers(is_url)
##        self.wfile.write("<html><body>")
##        if is_url:
##            self.wfile.write("<p>200</p>")
##        else:
##            self.wfile.write("<p>400</p>")
##        self.wfile.write("<p>%s</p></body></html>" % seife)
#
#        #if is_url:
#        #    # start the celery chain
#        #    chain(load.s([seife]), ytie.s()).apply_async()
#
#@route('/note') # or @route('/note')
#def note():
#    return '''
#        <form action="/note" method="post">
#            <textarea cols="40" rows="5" name="note">
#            Some initial text, if needed
#            </textarea>
#            <input value="submit" type="submit" />
#        </form>
#    '''
#
#@post('/note') # or @route('/note', method='POST')
#def note_update():
#    note = bottle.request.forms.get('note')
#    # processing the content of the text frame hereV
#
#def run(server_class=HTTPServer, handler_class=Server, port=8000):
#    """ setting up the server parameter """
#    server_address = ('', port)
#    httpd = server_class(server_address, handler_class)
#    print 'Starting httpd on port ' + str(port)
#    httpd.serve_forever()
#
#if __name__ == "__main__":
#    run()
