#!/usr/bin/env python
#

from celery import Celery
import youtube_dl

# create celery tasks and define communication channels
task_load = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
task_ytie = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
task_plex = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

## define tasks
# task to load a video and convert it into mp3
@task_load.taks
def load(url_path):
  ## define inner functions
  # youtube_dl filename-hook
  def ydl_filename_hook(dl_process):
    global filename
    filename = dl_process['filename']

  # define a dict with all options for youtube_dl
  #  append value to nested dict: ydl_opts['postprocessors'].append({'new_key2' : 'new_val2'})
  #  append value to dict:        ydl_opts.update({'new_key2' : 'new_val2'})
  ydl_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
      'key': 'FFmpegExtractAudio',
      'preferredcodec': 'mp3',
      'preferredquality': '192',
      }],
    'progress_hooks': [ydl_filename_hook],
    }

  with youtube_dl.YoutubeDL(ydl_options) as ydl:
    ydl.download(url)

  return filename
