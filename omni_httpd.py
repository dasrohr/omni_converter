#!/usr/bin/env python
"""
simple HTTP server in python
serve a simple form to use the OMNI Downloader
"""

''' pre checks '''
# check python version
try:
    from sys import version_info as py_version
    assert py_version >= (3,5)
except:
    exit('Python Version 3 is required')

# import the configuration calues from file
from yaml import safe_load as config_load
from os import path
if path.isfile()
    config = config_load(open("./config.yml"))
else:
    exit('Missing config file')

# make sure we have all modules we need available
try:
    from celery import Celery
    from omni_tasks import handler
    from validators import url as validate_url
    from urllib import parse
    from hashlib import sha512 as create_hash
    from bottle import template, get, post, request, run, abort, static_file, auth_basic, route
    import database
except ImportError:
    exit('please ensure that all required modules are installed: celery, validators, hashlib, bottle & that omni_tasks.py is available')

# init database connection (sqlite)
db = database.init(config['database_file'])

''' ======================================================= '''

def check_cred(user, pw):
    '''
    basic user and password check
    use a SSHA512 (salted) hashed password from sqlite-db and check if the entered username and password matches
    '''
    # query for stored secret in DB
    secret = database.get_secret(db, user)
    # if user is not known, get_secret returns False
    if not secret:
        return False
    db_hash, salt = secret.split(':')
    del secret
    # create hash from entered password using salt form secret
    pw = create_hash(pw.encode() + salt.encode()).hexdigest()
    if pw == db_hash:
        return True
    return False

@get('/')
@auth_basic(check_cred)
def serve_form():
    ''' serve the form '''
    return static_file('src/form.html', root='.')

@post('/')
@auth_basic(check_cred)
def post_form():
    ''' handle the POST data from the form '''
    values = {}
    for item in request.forms:
        value = request.forms.get(item)
        if not value:
            value = None
        values[item] = value

    # if we entered a url, is not valid, http400
    if 'url' in values:
        if values['url'] and not validate_url(values['url']):
            abort(400, 'inval - ' + values['url'])
        # if we entered nothing - no url & no ids, http400
        if not values['url'] and not values['vid'] and not values['pid']:
            abort(400, 'empty')
        # extract the id from url defined by target
        if values['target'] == 'v':
            try:
                values['vid'] = parse.parse_qs(parse.urlsplit(values['url']).query)['v'][0]
            except KeyError:
                abort(400, 'no videoID in URL')
        elif values['target'] == 'p':
            try :
                values['pid'] = parse.parse_qs(parse.urlsplit(values['url']).query)['list'][0]
            except KeyError:
                abort(400, 'no playlistID in URL')
        del values['target']

    # delete alb and albart values if not set
    if 'albart' in values and not values['albart']:
        del values['albart']
    if 'alb' in values and not values['alb']:
        del values['alb']

    # start the Handler to initiate Download
    handler.delay(**values)

    # answer to user, show values if debug = true
    if 'debug' in values.keys() and values['debug']:
        return template("{{dict}}", dict=values)
    return 'ok'

@route('/src/<filename>')
@auth_basic(check_cred)
def server_static(filename):
    ''' serve files in ./src/ '''
    return static_file(filename, root='./src/')

run(host="0.0.0.0", port=4000)

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
