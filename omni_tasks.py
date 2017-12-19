#!/usr/bin/env python
#

from celery import Celery
import youtube_dl
import datetime

# create celery tasks and define communication channels - we are just using simple redis
task_load = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
task_ytie = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
task_plex = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

## define tasks
# task to load a video and convert it into mp3
@task_load.task
def load(url_path):
  ## define inner functions
  # youtube_dl filename-hook to get the filename from the downloader
  def ydl_filename_hook(dl_process):
    global filename
    filename = dl_process['filename']

  ## modify the ydl_options
  # skip the download (dry-run)
  def disable_download():
    global do_download
    do_download = None
    ydl_opts.update({'skip_download' : 'true'})

  # enable debug
  def enable_debug():
    ydl_opts.pop('quiet', None)
    ydl_opts.update({'verbose' : 'true'})

  # enable download of a whole playlist
  def enable_list():
    # not sure how this behaves in terms of what the hook spits out and depending on that
    #  how to kick-off the next tasks for all the files in the list
    print('we are loading a list ... normaly')

  ## define variables
  # current year, month and KW for path building
  date_week = datetime.datetime.today().strftime("%W")
  date_year = datetime.datetime.today().strftime("%Y")
  date_month = datetime.datetime.today().strftime("%m")

  # build path to store files in
  # plex translates this to       /    albumartist                     /    album                      / title.ext
  file_path = "/store/omni_convert/" + date_year + "-" + date_month + "/" + date_year + "-" + date_week

  # define a dict with default options for youtube_dl
  #  append value to nested dict: ydl_opts['postprocessors'].append({'new_key2' : 'new_val2'})
  #  append value to dict:        ydl_opts.update({'new_key2' : 'new_val2'})
  #  remove value from dict:      ydl_opts.pop('key_12', None)
  ydl_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
      'key': 'FFmpegExtractAudio',
      'preferredcodec': 'mp3',
      'preferredquality': '320',
      }],
    'progress_hooks': [ydl_filename_hook],
    'noplaylist': 'True',
    'outtmpl': file_path + '/%(title)s.%(ext)s',
    'quiet': 'true',
    }
    # options for later implement when we go live
    #  quiet : ture
    #  verbose : true - switch with quiet
    # WHAT HAPPENS WITH THE HOOK, WHEN WE DOWNLOAD A PLAYLIS???

  # convert passed unicode to string and
  # process the passed url_path and extract the video-url and the options
  url_path = str(url_path)
  type(url_path)
  url_path = url_path[1:]
  values = url_path.split('::')
  url = values[0]

  # if we got a url, than remove it from the option-array
  if url:
    values.remove(values[0])

    # build a dict with options we can process to change the download behaviour
    #  if the value is passed - { 'passed_value' : 'function name' }
    options = {'nodl': disable_download,
               'debug': enable_debug,
               'list': enable_list,
              }
    # process the passed options, if there are some
    for option in values:
      try:
        options[option]()
      except KeyError:
        print('invalid option: ' + option)

    # download
    with youtube_dl.YoutubeDL(ydl_options) as ydl:
      ydl.download(url)

  else:
    print('we received no url')

  # return the filename of the loaded file for the text task
  return filename

# task to perform the YTIE filename-cleanup
@task_ytie.task
def ytie(filename):
  print('you see me rollin ... ' + filename)
