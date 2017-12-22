#!/usr/bin/env python
""" the task definitions for the celery worker """

import datetime
import os
import pwd
import grp
from celery import Celery
import youtube_dl

# create celery tasks and define communication channels - we are just using simple redis
TASK_LOAD = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_YTIE = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_PLEX = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

# declare global variables
# declare empty dict o store Filenames in given by the Download Hook
FILENAME = []
# switch to activate/deactivate playlist download (default = False)
SW_LIST = False
# default filename pattern used by ydl
FILE_NAME_PATTERN = '%(title)s.%(ext)s'

## define tasks
@TASK_LOAD.task
def load(url_path):
    """ task to load a video and convert it into mp3 """
    def ydl_filename_hook(dl_process):
        """ youtube_dl filename-hook to get the filename from the downloader """
        global FILENAME
        name = str(dl_process['filename'].rsplit('.', 1)[0])    # get the filename
#        name = str(name.rsplit('.', 1)[0])  # cutoff the filt-ext
        if name not in FILENAME:
            FILENAME.append(str(name))  # if the filename is not already in FILENAME add it

    def disable_download():
        """ set option to skip the download (dry-run) """
        ydl_options.update({'skip_download' : 'true'})

    def enable_debug():
        """ enable debug """
        ydl_options.pop('quiet', None)
        ydl_options.update({'verbose' : 'true'})

    def enable_list():
        """ enable download of a whole playlist """
        global SW_LIST
        global FILE_NAME_PATTERN
        SW_LIST = True
        FILE_NAME_PATTERN = '%(title)s_%(playlist_title)s.%(ext)s'
        ydl_options.pop('noplaylist', None)

    # build path to store files in as unicode so that youtube-dl is not complaining
    file_path_root = '/tmp/omni_cache/'

    # define a dict with default options for youtube_dl
    #    append value to nested dict: ydl_opts['postprocessors'].append({'new_key2' : 'new_val2'})
    #    append value to dict:        ydl_opts.update({'new_key2' : 'new_val2'})
    #    remove value from dict:      ydl_opts.pop('key_12', None)
    ydl_options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
            }],
        'progress_hooks': [ydl_filename_hook],
        'noplaylist': 'True',
        'quiet': 'true',
        }

    # convert passed unicode to string and
    # process the passed url_path and extract the video-url and the options
    url_path = str(url_path)
    url_path = url_path[4:-2]
    values = url_path.split('::')
    url = [values[0]]

    # if we got a url, than remove it from the option-list (values[])
    if url:
        values.remove(values[0])

        # build a dict with options we can process to change the download behaviour
        #   if the value is passed - { 'passed_value' : 'function name' }
        options = {'nodl': disable_download,
                   'debug': enable_debug,
                   'list': enable_list,
                  }
        # process the passed options, if there are some and they are valid
        for option in values:
            try:
                options[option]()
            except KeyError:
                print 'invalid option: ' + option

        # build thefilename pattern and path we store the files at ...
        file_path = unicode(file_path_root + FILE_NAME_PATTERN)
        # ... and add it to our ydl_options
        ydl_options.update({'outtmpl' : file_path})

        # download
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            ydl.download(url)

    else:
        print 'we received no url'

    # build our tuple to pass it to the next task
    arguments = (FILENAME, file_path_root, SW_LIST)
    # return the tuple
    return arguments

# task to perform the YTIE filename-cleanup
@TASK_YTIE.task
def ytie(arguments):
    """ more to come ... """
    import subprocess
    print 'you see me rollin ... '

    # collect our arguments
    filenames, file_path, sw_list = arguments

    # current year, month and KW for path and tag building
    date_week = datetime.datetime.today().strftime("%W")
    date_year = datetime.datetime.today().strftime("%Y")
    date_month = datetime.datetime.today().strftime("%m")

    # build mp3-tags
    if sw_list:
        # since we add the playlist name from the filename, we have to remove it from all filenames
        tag_albumartist = 'playlists'
        tag_album = str(filenames[0].split('_')[1]) # set the playlist name as album
        for filename in filenames:
            name = str(filename.split('_')[0])
            filenames.remove(filename)
            filenames.append(name)
    else:
        tag_albumartist = date_year + '-' + date_month
        tag_album = date_year + '-' + date_week

    # define the root path where plex stores the files
    plex_path_root = '/store/omni_convert/'

    # get uid and gid of user 'plex'
    uid = pwd.getpwnam("plex").pw_uid
    gid = grp.getgrnam("plex").gr_gid

    # create a list for the filenames which has been cleaned by YTIE
    filenames_clean = []
    for filename in filenames:
        ytie_cmd = subprocess.Popen('java -jar YTIE/ExtractTitleArtist.jar -use YTIE/model/ ' + \
                   filename, shell=True, stdout=subprocess.PIPE)
        for line in ytie_cmd.stdout:
            # parse the YTIE output and catch the cases where YTIE fails to detect things,
            #  so that we do not end in empty filenames/tags
            if "Artists" in line:
                artist = line.split(': ')[1].rstrip()
                if not artist:
                    artist = 'Unknown Artist'
            elif "Title" in line:
                title = line.split(': ')[1].rstrip()
                if not title:
                    title = 'Unknown Title'
            elif "Remix" in line:
                rmx = line.split(': ')[1].rstrip()
                if rmx:
                    title = title + '(' + rmx + ')'
            # build a list with the new filenames to pass them later
            print 'artist: ' + artist + '  - title: ' + title
            filename_clean = artist + " - " + title + ".mp3"
            print 'filename_cleaned: ' + filename_clean
            filenames_clean.append(filename_clean)

        ###
        # MP3TAG STUFF HERE
        ###

        plex_path = plex_path_root + tag_albumartist + '/' + tag_album
        if not os.path.exists(plex_path):
            os.makedirs(plex_path)
            # set perminssions on dir
            os.chown(plex_path, uid, gid)
            os.chmod(plex_path, 770)

        # move the file and set the permissions
        os.rename(file_path + filename, plex_path + filename_clean)
        os.chown(plex_path + filename_clean, uid, gid)
        os.chmod(plex_path + filename_clean, 660)
        