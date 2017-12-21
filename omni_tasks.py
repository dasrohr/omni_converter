#!/usr/bin/env python
""" the task definitions for the celery worker """

import datetime
from celery import Celery
import youtube_dl

# create celery tasks and define communication channels - we are just using simple redis
TASK_LOAD = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_YTIE = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_PLEX = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

# declare empty dict o store Filenames in given by the Download Hook
FILENAME = {}

## define tasks
@TASK_LOAD.task
def load(url_path):
    """ task to load a video and convert it into mp3 """
    def ydl_filename_hook(dl_process):
        """ youtube_dl filename-hook to get the filename from the downloader """
        global FILENAME
        tmp_name = dl_process['filename']
        tmp_stat = dl_process['status']
        tmp_name = str(tmp_name.rsplit('.', 1)[0])
        FILENAME[tmp_name] = str(tmp_stat)

    def disable_download():
        """ set option to skip the download (dry-run) """
        ydl_options.update({'skip_download' : 'true'})

    def enable_debug():
        """ enable debug """
        ydl_options.pop('quiet', None)
        ydl_options.update({'verbose' : 'true'})

    def enable_list():
        """ enable download of a whole playlist """
        ydl_options.pop('noplaylist', None)

    ## define variables
    # current year, month and KW for path building
    date_week = datetime.datetime.today().strftime("%W")
    date_year = datetime.datetime.today().strftime("%Y")
    date_month = datetime.datetime.today().strftime("%m")

    # build path to store files in as unicode so that youtube-dl is not complaining
    file_path = unicode("/store/omni_convert/" + date_year + "-" + date_month + \
                "/" + date_year + "-" + date_week + '/%(title)s.%(ext)s')

    # define a dict with default options for youtube_dl
    #    append value to nested dict: ydl_opts['postprocessors'].append({'new_key2' : 'new_val2'})
    #    append value to dict:                ydl_opts.update({'new_key2' : 'new_val2'})
    #    remove value from dict:            ydl_opts.pop('key_12', None)
    ydl_options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
            }],
        'progress_hooks': [ydl_filename_hook],
        'noplaylist': 'True',
        'outtmpl': file_path,
        'quiet': 'true',
        }

    # convert passed unicode to string and
    # process the passed url_path and extract the video-url and the options
    url_path = str(url_path)
    url_path = url_path[4:-2]
    values = url_path.split('::')
    url = [values[0]]

    # if we got a url, than remove it from the option-array
    if url:
        values.remove(values[0])

        # build a dict with options we can process to change the download behaviour
        #    if the value is passed - { 'passed_value' : 'function name' }
        options = {'nodl': disable_download,
                   'debug': enable_debug,
                   'list': enable_list,
                  }
        # process the passed options, if there are some
        for option in values:
            try:
                options[option]()
            except KeyError:
                print 'invalid option: ' + option

        # download
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            ydl.download(url)

    else:
        print 'we received no url'

    # return the filename of the loaded file for the text task
    return FILENAME

# task to perform the YTIE filename-cleanup
@TASK_YTIE.task
def ytie(filename):
    """ more to come ... """
    print 'you see me rollin ... '
    print filename
    print type(filename)
    print str(filename.keys())
    print type(filename.keys()[0])
