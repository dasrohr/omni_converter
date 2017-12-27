#!/usr/bin/env python
""" the task definitions for the celery worker """

import datetime
import os
import pwd
import grp
from celery import Celery
import youtube_dl
import eyed3

# create celery tasks and define communication channels - we are just using simple redis
TASK_LOAD = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_YTIE = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_PLEX = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

## define tasks
@TASK_LOAD.task(bind=True)
def load(self, url_path):
    """ task to load a video and convert it into mp3 """
    # declare global variables
    # declare empty dict o store Filenames in given by the Download Hook
    filename = []
    # switch to activate/deactivate playlist download (default = False)
    sw_list = False
    # default filename pattern used by ydl
    file_name_pattern = '%(title)s.%(ext)s'
    def ydl_filename_hook(dl_process):
        """ youtube_dl filename-hook to get the filename from the downloader """
        #global filename
        name = str(dl_process['filename'].rsplit('.', 1)[0].rsplit('/', 1)[1])    # get the filename
        if name not in filename:
            filename.append(str(name))  # if the filename is not already in filename add it

    # build path to store files in as unicode so that youtube-dl is not complaining
    file_path_root = '/tmp/omni_convert/'

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
    if url[0] != '':
        values.remove(values[0])

        # process the options if there are any
        for option in values:
            if option == 'nodl':
                # set option to skip the download (dry-run)
                ydl_options.update({'skip_download' : 'true'})
            elif option == 'list':
                # enable download of a whole playlist
                sw_list = True
                file_name_pattern = '%(title)s_%(playlist_title)s.%(ext)s'
                ydl_options.pop('noplaylist', None)
            elif option == 'debug':
                # enable debug
                ydl_options.pop('quiet', None)
                ydl_options.update({'verbose' : 'true'})
            else:
                print 'invalid option: ' + option

        # build thefilename pattern and path we store the files at ...
        file_path = unicode(file_path_root + file_name_pattern)
        # ... and add it to our ydl_options
        ydl_options.update({'outtmpl' : file_path})

        # DEBUG
        print ydl_options
        print str(file_name_pattern)
        print filename
        print url
        print sw_list
        print values

        # download
        with youtube_dl.YoutubeDL(ydl_options) as ydl:
            print 'url(' + str(url) + ') url_path (' + str(url_path) + ')'
            ydl.download(url)


    else:
        print 'we received no url'
        self.request.callbacks = None
        return

    # build our tuple to pass it to the next task
    arguments = (filename, file_path_root, sw_list)

    # DEBUG
    print arguments

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
        print filenames[0]
        tag_album = str(filenames[0].split('_')[1]) # set the playlist name as album
    else:
        tag_albumartist = date_year + '-' + date_month
        tag_album = date_year + '-' + date_week

    # define the root path where plex stores the files
    plex_path_root = '/store/omni_convert/'

    # get uid and gid of user 'plex'
    uid = pwd.getpwnam("plex").pw_uid
    gid = grp.getgrnam("plex").gr_gid

    # create a list for the filenames which has been cleaned by YTIE
    for filename in filenames:
        ytie_cmd = subprocess.Popen('java -jar /opt/omni_converter/YTIE/ExtractTitleArtist.jar \
                   -use /opt/omni_converter/YTIE/model/ ' + \
                   '"' + str(filename.split('_')[0]) + '"', shell=True, stdout=subprocess.PIPE)
        for line in ytie_cmd.stdout:
            # parse the YTIE output and catch the cases where YTIE fails to detect things,
            #  so that we do not end in empty filenames/tags
            if "Artists" in line:
                try:
                    tag_artist = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_artist = 'Unknown Artist'

            elif "Title" in line:
                try:
                    tag_title = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_title = 'Unknown Title'

            elif "Remix" in line:
                try:
                    tag_rmx = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_rmx = False
                if tag_rmx:
                    tag_title = tag_title + '(' + tag_rmx + ')'

        # build a list with the new filenames to pass them later
        filename_clean = tag_artist + " - " + tag_title + ".mp3"

        # set the mp3Tags
        audiofile = eyed3.load(file_path + filename + ".mp3")
        audiofile.tag.artist = unicode(tag_artist)
        audiofile.tag.title = unicode(tag_title)
        audiofile.tag.album = unicode(tag_album)
        audiofile.tag.album_artist = unicode(tag_albumartist)
        audiofile.tag.save()

        plex_path = plex_path_root + tag_albumartist + '/' + tag_album + '/'
        if not os.path.exists(plex_path):
            os.makedirs(plex_path)
            # set perminssions on dir
            try:
                os.chown(plex_path, uid, gid)
                os.chmod(plex_path, 0770)
            except OSError:
                print 'error while set permission on ' + plex_path

        # move the file and set the permissions
        try:
            os.rename(file_path + filename + '.mp3', plex_path + filename_clean)
            os.chown(plex_path + filename_clean, uid, gid)
            os.chmod(plex_path + filename_clean, 0660)
        except OSError:
            print 'error while moving file or setting permissions'
        