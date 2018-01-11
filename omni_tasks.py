#!/usr/bin/env python
""" the task definitions for the celery worker """

from __future__ import unicode_literals
import datetime
import os
import re
import pwd
import grp
from difflib import get_close_matches
from unidecode import unidecode
from celery import Celery
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import youtube_dl
import eyed3

# create celery tasks and define communication channels - we are just using simple redis
TASK_LOAD = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_YTIE = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')
TASK_PLEX = Celery('omni_convert', backend='redis://localhost', broker='redis://localhost')

## define tasks
@TASK_LOAD.task
def load(url_path):
    """ task to load a video and convert it into mp3 """
    # declare defaults
    # declare empty dict o store Filenames in from the Download Hook
    filename = []
    # switch to activate/deactivate playlist download (False)
    sw_list = False
    # default filename pattern used by ydl (videotitle.ext)
    file_name_pattern = '%(title)s.%(ext)s'
    # default setting for debuging (False)
    debug = False
    # set the folder to a default (False)
    folder = False
    # set the folder security switch to a deafult (False)
    sw_new_folder = False

    def ydl_filename_hook(dl_process):
        """ youtube_dl filename-hook to get the filename from the downloader """
        name = dl_process['filename'].rsplit('.', 1)[0].rsplit('/', 1)[1]
        if name not in filename:
            filename.append(name)

    # build path to store files in as unicode so that youtube-dl is not complaining
    file_path_root = '/tmp/omni_convert/'

    # define a dict with options for youtube_dl
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

    # extract the url and options from url_path
    #   (url_path is a list with one entry which is a unicode)
    url = [str(url_path[0])[1:].split('::')[0]]
    values = str(url_path[0])[1:].split('::')[1:]
    # compile regex-pattern to detect folder-option
    regex_folder = re.compile('folder=.*')

    # process the options if there are any
    for option in values:
        if option == 'nodl':
            # set option to skip the download (dry-run)
            ydl_options.update({'skip_download' : 'true'})
        elif regex_folder.match(option):
            # set the plex-folder we want to store in later
            # this value gets passed to the ytie task, it is not used in this task
            if debug: print 'DEBUG :: option -> {}'.format(option)
            folder = option.split('=')[1].replace('_', ' ')
        elif option == 'new':
            sw_new_folder = True
        elif option == 'list':
            # enable download of a whole playlist
            sw_list = True
            file_name_pattern = '%(title)s__%(playlist_title)s.%(ext)s'
            ydl_options.pop('noplaylist', None)
        elif option == 'debug':
            # enable debug
            debug = True
            ydl_options.pop('quiet', None)
            ydl_options.update({'verbose' : 'true'})
        else:
            print 'ERROR :: invalid option:\t{}'.format(option)

    # build thefilename pattern and path we store the files at ...
    file_path = unicode(file_path_root + file_name_pattern)
    # ... and add it to our ydl_options
    ydl_options.update({'outtmpl' : file_path})
    if debug: print 'DEBUG ::\nurlpath\t{}\nurl\t{}\noptions\t{}\nlistsw\t{}\nfolder\t{}\nnew folder\t{}\nydl_opt\t{}'.format(url_path, url, values, sw_list, folder, sw_new_folder, ydl_options)
    # download
    with youtube_dl.YoutubeDL(ydl_options) as ydl:
        ydl.download(url)

    # build our tuple to pass it to the next task
    arguments = (filename, file_path_root, sw_list, debug, folder, sw_new_folder)

    if debug: print 'DEBUG :: task results\t{}'.format(arguments)

    # return the tuple
    return arguments

# task to perform the YTIE filename-cleanup
@TASK_YTIE.task
def ytie(arguments):
    """
    this defines a task which uses the list of filenames from the previous task
    and performs YTIE operations on it, renames the files acordingly and moves
    them to the right position
    """
    import subprocess

    # collect our arguments
    filenames, file_path, sw_list, debug, folder, sw_new_folder = arguments

    if debug: print 'DEBUG ::\nfiles\t{}\npath\t{}\nlistsw\t{}\nfolder\t{}\nnew folder\t{}'.format(filenames, file_path, sw_list, folder, sw_new_folder)

    # current year, month and KW for path and tag building
    date_week = datetime.datetime.today().strftime("%W")
    date_year = datetime.datetime.today().strftime("%Y")
    date_month = datetime.datetime.today().strftime("%m")

    # define the root path where plex stores the files
    plex_path_root = '/store/omni_convert/'

    # get uid and gid of user 'plex'
    uid = pwd.getpwnam("plex").pw_uid
    gid = grp.getgrnam("plex").gr_gid

    # build mp3-tags
    if folder:
        # if we got passed a foldername, it is used as albumartist, so that the paths got build correctly to store and it gets created if it doe not exists
        #  - if the switch sw_new_folder == True, then we just using the passed string as foldername
        #  - if the switch sw_new_folder == Fasle, then we do a check on the existing folders and find the closed match and use the match as foldername/albumartist
        #      so it is ensured that typos are not passed any further and we end up in a messy folder structure on the fs and plex
        #  - we can handle the follwoing syntax in folder: albumartist/album & albumartist (case 2 sets album = year-kw)
        #      this allows to create a new albumartist/album structure. close_matches are performed on both values, if there is sw_new_folder == False
        #  - modify cutoff= value to set how close foldername has to match an existing one (lower means less equality) - default = 0.6
        try:
            tag_albumartist, tag_album = folder.split('/')
        except ValueError:
            tag_albumartist = folder
            tag_album = date_year + '-' + date_week

        if debug: print 'DEBUG :: albumartist & album before close_match \nalbumartist\t{}\nalbum\t{}'.format(tag_albumartist, tag_album)

        if not sw_new_folder:
            tag_albumartist = get_close_matches(tag_albumartist, os.listdir(plex_path_root), n=1, cutoff=0.2)
            if not tag_albumartist:
                tag_albumartist = 'drunk idiot'
            if os.path.exists(plex_path_root + tag_albumartist):
                tag_album = get_close_matches(tag_album, os.listdir(plex_path_root + tag_albumartist), n=1, cutoff=0.2)
                if not tag_album:
                    tag_album = 'go home'

            if debug: print 'DEBUG :: albumartist & album after close_match\nalbumartist\t{}\nalbum\t{}'.format(tag_albumartist, tag_album)

    else:
        tag_albumartist = date_year + '-' + date_month
        tag_album = date_year + '-' + date_week

    if sw_list:
        # if we load a playlist, use the list name as album ...
        if isinstance(filenames[0], unicode):
            filenames[0] = unidecode(filenames[0])
        tag_album = str(filenames[0].split('__')[1]) # set the playlist name as album
    else:
        # ... else generate the default album name (year-week)
        tag_album = date_year + '-' + date_week

    # create a list for the filenames which has been cleaned by YTIE
    for filename in filenames:
        # get rid of unicode characters if we have any and rename the loaded file
        if isinstance(filename, unicode):
            unifree_filename = unidecode(filename)
            os.rename(file_path + filename + '.mp3', file_path + unifree_filename + '.mp3')
            filename = unifree_filename
        ytie_cmd = subprocess.Popen('java -jar /opt/omni_converter/YTIE/ExtractTitleArtist.jar \
                   -use /opt/omni_converter/YTIE/model/ ' + \
                   '"' + filename.split('__')[0] + '"', shell=True, stdout=subprocess.PIPE)
        for line in ytie_cmd.stdout:
            # parse the YTIE output and catch the cases where YTIE fails to detect things,
            #  so that we do not end in empty filenames/tags
            if 'Artists' in line:
                try:
                    tag_artist = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_artist = 'Unknown Artist'

            elif 'Title' in line:
                try:
                    tag_title = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_title = 'Unknown Title'

            elif 'Remix' in line:
                try:
                    tag_rmx = line.split(': ')[1].rstrip()
                except IndexError:
                    tag_rmx = False
                if tag_rmx:
                    tag_title = tag_title + '(' + tag_rmx + ')'

        # build the old filename for easier reference
        file_old = file_path + filename + '.mp3'

        # open file, decide if we load a MIX or not, depending on the track length and write mp3-tags
        audiofile = eyed3.load(file_old)
        if not sw_list and audiofile.info.time_secs >= 1200:
            # if we are not loading a list and the song is longer than 20min, mark the album with ' [MIX]'
            if debug: print 'DEBUG :: Track length: {}'.format(audiofile.info.time_secs)
            tag_album = tag_album + ' [MIX]'

        audiofile.tag.artist = unicode(tag_artist)
        audiofile.tag.title = unicode(tag_title)
        audiofile.tag.album = unicode(tag_album)
        audiofile.tag.album_artist = unicode(tag_albumartist)
        audiofile.tag.save()

        # build paths to plex library for easier reference
        plex_path_artist = plex_path_root + tag_albumartist + '/'
        plex_path = plex_path_artist + tag_album + '/'

        # create plex folders if not exist
        if not os.path.exists(plex_path):
            if debug: print 'DEBUG :: create new plex-dir {}'.format(plex_path)
            os.makedirs(plex_path)
            # set perminssions on dir
            try:
                os.chown(plex_path, uid, gid)
                os.chmod(plex_path, 0770)
            except OSError:
                print 'ERROR :: error while set permission on {}'.format(plex_path)

        # build the new file name for easier reference
        file_new = plex_path + tag_artist + ' - ' + tag_title + '.mp3'

        ## ALBUM cover generator
        # generate text for album cover
        cover_album_text = tag_album
        text_length = len(cover_album_text)
        text_max_length = 20
        # if text is longer than text_max_length, then strip it
        if text_length >= text_max_length:
            cover_album_text = cover_album_text[:text_max_length]
            text_length = len(cover_album_text)
        # if last char is space, strip it off
        if cover_album_text[-1] == ' ':
            cover_album_text = cover_album_text[:-1]
            text_length = len(cover_album_text)

        # build the name of the cover-jpg and check if it already exists. Skip if true
        album_cover = plex_path + 'poster.jpg'

        # create album cover, if it dos not already exists
        if not os.path.exists(album_cover):
            # open image
            cover = Image.open('res/black.jpg')
            # get size of our template image
            image_x, image_y = cover.size
            # enable drawing
            draw = ImageDraw.Draw(cover)
            # calc the font size depending on the image size and ammount of characters
            font_size = (2 * image_y) / text_length
            # calc the y_offset for the text, depending on the font size
            text_offset = (image_x - font_size) / 2
            # set font type and size
            font = ImageFont.truetype("UbuntuMono-B.ttf", font_size)
            # be picasso
            draw.text((0, text_offset), cover_album_text, (255, 255, 255), font=font)
            # save image
            cover.save(album_cover)
        elif debug:
            font_size = 'not calculated'
            image_x = 'not calculated'
            image_y = 'not calculated'
            text_offset = 'not calculated'

        if debug: print 'DEBUG ::\nALBUM-Cover\ntag artist:\t{}\ntag title:\t{}\ntag album:\t{}\ntag album art.:\t{}\nfile cover:\t{}\ncover text:\t{}\ncover text len:\t{}\ncover text size:\t{}\ncover size x:\t{}\ncover size y:\t{}\ncover offset y:\t{}\n'.format(tag_artist, tag_title, tag_album, tag_albumartist, album_cover, cover_album_text, text_length, font_size, image_x, image_y, text_offset)


        ## ARTIST cover generator
        # generate text for artist cover
        cover_artist_text = tag_albumartist
        text_length = len(cover_artist_text)
        # if text is longer than text_max_length, then strip it
        if text_length >= text_max_length:
            cover_artist_text = cover_artist_text[:text_max_length]
            text_length = len(cover_artist_text)
        # if last char is space, strip it off
        if cover_artist_text[-1] == ' ':
            cover_artist_text = cover_artist_text[:-1]
            text_length = len(cover_artist_text)

        # build the name of the cover-jpg and check if it already exists. Skip if true
        artist_cover = plex_path_artist + 'poster.jpg'

        # create artist cover, if it dos not already exists
        if not os.path.exists(artist_cover):
            # open image
            cover = Image.open('res/black.jpg')
            # get size of our template image
            image_x, image_y = cover.size
            # enable drawing
            draw = ImageDraw.Draw(cover)
            # calc the font size depending on the image size and ammount of characters
            font_size = (2 * image_y) / text_length
            # calc the y_offset for the text, depending on the font size
            text_offset = (image_x - font_size) / 2
            # set font type and size
            font = ImageFont.truetype("UbuntuMono-B.ttf", font_size)
            # be picasso
            draw.text((0, text_offset), cover_artist_text, (255, 255, 255), font=font)
            # save image
            cover.save(artist_cover)
        elif debug:
            font_size = 'not calculated'
            image_x = 'not calculated'
            image_y = 'not calculated'
            text_offset = 'not calculated'

        if debug: print 'DEBUG ::\nARTIST-Cover\ntag artist:\t{}\ntag title:\t{}\ntag album:\t{}\ntag album art.:\t{}\nfile cover:\t{}\ncover text:\t{}\ncover text len:\t{}\ncover text size:\t{}\ncover size x:\t{}\ncover size y:\t{}\ncover offset y:\t{}\n'.format(tag_artist, tag_title, tag_album, tag_albumartist, artist_cover, cover_artist_text, text_length, font_size, image_x, image_y, text_offset)

        if debug: print 'DEBUG :: moving file\t{} -->> {}'.format(file_old, file_new)
        # move the file and set the permissions
        try:
            os.rename(file_old, file_new)
            os.chown(file_new, uid, gid)
            os.chmod(file_new, 0660)
        except OSError:
            print 'ERROR :: error while moving file or setting permissions'
