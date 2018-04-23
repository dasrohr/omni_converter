#!/usr/bin/env python
'''
side tasks performed by the omni_converter
written in another celery worker to esure the tasks are beeing executed, 
even if large downloads are blocking the slots
'''

from celery import Celery
from subprocess import run, PIPE
from yaml import safe_load as config_load

omni_side = Celery('omni_side', backend='rpc://localhost')

# load config
if path.isfile('./config.yml'):
    config = config_load(open("./config.yml"))
else:
    exit('Missing config file')


@omni_side.task()
def cover(text, folder):
  '''
  function to build the cover-images
  cover text is passed as first parameter (string)
  the folder to place the file ins passed as secpond paramater (string)
  '''
  # create image here

@omni_side.task
def ytie(string):
  '''
  runs the ytie on a given string which is mostlikely the title of a video
  returns two strings which represent the artist and the title, generated from the title
  if ytie detects a rmx, it gets attached to the title
  '''
  # define a poiter to /dev/null for waste management
  dev_null = open('/dev/null', 'w')

  # TODO: do not hardcode paths :(
  ytie_cmd = ['java', '-jar', './YTIE/ExtractTitleArtist.jar', '-use' './YTIE/model/', string]

  # TODO ugly pasta code - might be a better way ... works for now
  for line in run(cmd, stdout=PIPE, stderr=dev_null).stdout.decode('utf-8').replace('\t','').splitlines():
    if line.startswith('Artists: '):
      try:
        artist = line.split(': ')[1]
      except IndexError:
        artist = 'Unknown Artist'
    if line.startswith('Title: '):
      try:
        title = line.split(': ')[1]
      except IndexError:
        title = 'Unknown Title'
    if line.startswith('Remix: '):
      try:
        rmx = line.split(': ')[1]
      except IndexError:
        pass
  
  # if rmx detected and title not unknown, append rmx to title
  if rmx and title not == 'Unknown Title':
    title = title + " " + rmx

  # close the lid
  dev_null.close()

  return artist, title

@omni_side.task
def id3(art, title, alb, albart, file):
  '''
  docstring
  '''
  # stuff here

@omni_side.task
def cleanup():
    '''
    Task to check the files registered in the databse if they still exist
    '''
    # get all files and links from DB
    # check if all exist
    # remove DB entries if not
    # check if entry was the last in DB - remove from history if true
    # if a file was deleted, check if it had links, remove links too
    #   toughts: if delted file has many links, one song disapears from many places. might be not so good
    #            maybe provide a web interface to delete files and if it was a file and it has links, replace the links with a copy of that file (tags needs to be reset as alb and albart are changing)
    #            OR - if file with links got deleted, replace only ONE link with the file (and remove the original) and relink the now orphanded links to the new file. tags needs to be reset in that file as alb and albart are changing