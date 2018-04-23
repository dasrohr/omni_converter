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
if path.isfile('./config.yml'):
    config = config_load(open("./config.yml"))
else:
    exit('Missing config file')

# make sure we have all modules we need available
try:
    from celery import Celery
    from omni_tasks import main
    from validators import url as validate_url
    from urllib import parse
    from hashlib import sha512 as create_hash
    from bottle import template, get, post, request, run, abort, static_file, auth_basic, route
    import database
except Exception as e:
    print('error: {}'.format(e))
    exit('please ensure that all required modules are installed: celery, validators, hashlib, bottle & that omni_tasks.py is available')

# init database connection (sqlite)
db = database.connect(config['database_file'])

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
    main.delay(**values)

    # answer to user, show values if debug = true
    if 'debug' in values.keys() and values['debug']:
        return template("{{dict}}", dict=values)
    return 'ok'

@route('/src/<filename>')
@auth_basic(check_cred)
def server_static(filename):
    ''' serve files in ./src/ '''
    return static_file(filename, root='./src/')

@route('/src/status.html')
@auth_basic(check_cred)
def status():
    '''
    Show the Titles of the currently loaded Videos on Webpage
    Code is ugly as hell atm - this works but shure there are smarter ways of doing this
    '''
    import json
    tasks = []
    inspect_out = inspect('active')
    # extra for needed as Celery packs the values in a dict with the hostname as key
    if inspect_out:
        for key in inspect_out.keys():
            for task in inspect_out[key]:
                tasks.append(json.loads(task['kwargs'].replace("'", "\"").replace("None", "\"None\"").replace("False", "\"False\"").replace("[{...}]", "\"gen\""))['source_title'])

    return template('./src/status.html', names = tasks, history = database.get_status_histroy(db))

def inspect(method):
    '''
    inspect function to interact with Celery
    '''
    app = Celery('app')
    return getattr(app.control.inspect(), method)()


if 'port' in config:
    port = config['port']
else:
    port = 4000

run(host="0.0.0.0", port=port)
