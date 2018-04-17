#!/usr/bin/env python
""" the task definitions for the celery worker """

#from __future__ import unicode_literals
#import datetime
#import os
#import re
#import pwd
#import grp
#from PIL import Image
#from PIL import ImageDraw
#from PIL import ImageFont
#import eyed3

''' pre checks '''
# check python version
try:
    from sys import version_info as py_version
    assert py_version >= (3,5)
except:
    exit('Python Version 3 is required')

import youtube_dl
import database
import string
import random
from celery import Celery
from requests import get
from urllib.parse import urlparse
from yaml import safe_load as config_load
from datetime import datetime as date
from os import symlink, path, walk, makedirs
from os import rename as move
from difflib import get_close_matches

# load the config from file
if path.isfile('./config.yml'):
    config = config_load(open("./config.yml"))
else:
    exit('Missing config file')

# If there is no DB File, create and initialize a new one
if not path.isfile(config['database_file']):
    database.initialize_db(config['database_file'])
# open the database connection to the db-file from the config
db = database.connect(config['database_file'])

# create celery applicatoin and define communication broker
omni = Celery('omni_worker', brocker='redis://localhost')

class Video:
    def __init__(self, **kwargs):
        self.playlist = None                                    # initiate attribute to store the playlist title in it, if there is one
        self.playlist_id = None                                 # initiate attribute to store the playlist ID in, if there is one
        self.filename = gen_filename()                          # file name (random string with 20 chars)
        self.art = None                                         # initiate the artist
        self.title = None                                       # initiate the title (id3-title)
        self.albart = None                                      # initiate the albart
        self.alb = None                                         # initiate the alb
        self.date = date.now().strftime('%Y-%m-%d %H:%M:%S')    # date when this download is executed (now)
        self.target = None                                      # initiate the target attribute so that the DB entry can set to NULL. The target is the file the symlinks targets in case we have to symlink
        self.type = 'f'                                         # default indicator if final result is a file or a link - "l" = link
        self.force_folder = False                               # default inidicator if we enforce the path if custom alb/albart entered
        self.debug = False                                      # default debug state
        self.simulate = False                                   # default simulate state - no download if true TODO: this might be quiet dangerous atm as this gets ignored foer all other stepps (!!!) think about removing!

        # set attributes from passed kwargs
        for key, value in kwargs.items():
            # translate 0 and 1 into True and False
            if value == '1':
                value = True
            elif value == '0':
                value = False
            setattr(self, key, value)
        
        # build the url to the video
        # TODO: atm, youtube is hardcoded - this needs to be flexible for more serivces (SoundCloud etc.)
        #       this includes that the webform needs to be smarter as well - have a feeling as this will be complicated to implement
        self.url = 'https://www.youtube.com/watch?v=' + self.id

        # parse the URL for the Website name
        self.source = urlparse(self.url).netloc.replace('www.', '').split('.')[0]

        # build the path attribute depending on what was entered in the form
        # when loading a playlist, the defaults are different, but the process of sorting things out is the same
        if self.playlist:
            self.build_path('playlists', self.playlist)
        else:
            self.build_path(date.now().strftime('%Y-%m'), date.now().strftime('%Y-KW%U'))

    def download(self):
        '''
        set options and Download
        also handle case were the ID is already in the History
        '''
        #TODO: catch case where the entered target does not exit (invalid YT url, ID, etc.)
        self.dl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
                }],
            'outtmpl': config['download_root'] + self.filename + '.%(ext)s',
            'quiet': 'True',
            'noplaylist': 'True',
        }
        # enable YTDL debuging
        if self.debug:
            self.dl_opts['quiet'] = 'False'

        # TODO make debug output
        print(self.__dict__)

        # check if the Video has already been downloaded by runnin the database Query
        if not database.check_id(db, self.id):
            database.add_to_history(db, **self.__dict__)
            # check the TODO from above ... catching case where url is invalid, target does not exist
            download.delay(**self.__dict__)
        # if the ID has been downloaded already, skip the dl and create a link to the loaded file
        else:
            self.type = 'l'
            # build the destination path for the symlink and db-entry
            self.target = path.join(*database.get_filename(db, self.id))
            # check if there is already a symlink to the file in the current Album
            if not database.check_for_existing_link(db, self.id, self.path):
                # create a Symlink
                symlink(self.target + '.mp3', path.join(self.path, self.filename + '.mp3'))
                # add entry to DB
                database.add_file(db, **self.__dict__)
                #TODO make debug only
                print('created link: ({}) -> ({})'.format(path.join(self.path, self.filename) + '.mp3', self.target + '.mp3'))
            
            print('{} already loaded'.format(self.id))
            if self.debug: print(self.__dict__)

    def build_path(self, def_albart, def_alb):
        '''
        create folders and build the path depending on the entered values
        also sets the albart and alb attributes to the desired value
        '''
        # default situation: nothing entered
        if not self.albart and not self.alb:
            self.albart = def_albart
            self.alb = def_alb

        # entered albart but not alb
        elif self.albart and not self.alb:
            self.alb = def_alb
            if not self.force_folder:
                self.albart = fuzzy_folder(self.albart)

        # special situation: entered no albart but alb
        elif not self.albart and self.alb:
            self.albart = def_albart
            if not self.force_folder:
                # note that this case can force the fuzzy match against an empty folder
                #  (albart got created, because it did not exist - causing an empty folder for fuzzy match)
                #  fuzzy_folder() is handling this case
                self.alb = fuzzy_folder(self.alb, depth = self.albart)

        # entered both
        elif self.albart and self.alb:
            if not self.force_folder:
                self.albart = fuzzy_folder(self.albart)
                self.alb = fuzzy_folder(self.alb, depth = self.albart)

        # TODO print only when debug
        print('atr after build_path: albart({}) alb({}) force({})'.format(self.albart, self.alb, self.force_folder))

        create_folder(self.albart, self.alb)
        self.path = path.join(config['plex_root'], self.albart, self.alb)

def create_folder(*sub_dirs, root = config['plex_root']):
    '''
    create a path recursive if not exist. 
    path is build for the given arguments in the order passed
    TODO: also set chown?
    '''
    for sub_dir in sub_dirs:
        root += sub_dir + '/'
    if not path.exists(root):
        makedirs(root, 0o740)

def get_ids_from_pl(pl_id, **opts):
    '''
    get all VideoIDs from all Videos stored in a Playlist
    need playlistID
    '''
    params = {
            'id': pl_id,
            'key': config['api_key'],
            'part': 'snippet',
            'maxResults': 50, 
            }
    url = config['api_base_url'] + 'playlists'
    playlist_title = get(url, params=params).json()['items'][0]['snippet']['title']

    # modify the parameter for the next API request
    del params['id']
    params['playlistId'] = pl_id

    url = config['api_base_url'] + 'playlistItems'
    ids = []
    for video in get(url, params=params).json()['items']:
        ids.append(Video(id = video['snippet']['resourceId']['videoId'], source_title = video['snippet']['title'], playlist = playlist_title, **opts))
    return ids

def get_title_from_id(id):
    '''
    get the titiel of a video form its ID
    '''
    url = config['api_base_url'] + 'videos'
    params = { 
            'id': id,
            'key': config['api_key'],
            'part': 'snippet',
            }
    return get(url, params=params).json()['items'][0]['snippet']['title']

def ytie(title):
    '''
    run the YTIE to clean the title
    needs a String (Title)
    returns 
    '''

def fuzzy_folder(string, depth = None, cutoff = 0.1):
    '''
    do a fuzzy match on folders in a path
    depth can be a string which will extend the default path to look in
    default path is config['plex_root']
    the default cutoff can be overwritten
    return the foldername with the closest match of given string
    '''
    print('fuzzy input: ({})'.format(string))
    work_dir = config['plex_root']
    if depth:
        work_dir = path.join(work_dir, depth)

    print('fuzzy path: ({})'.format(work_dir))
    # if we doing a fuzzy match on a folder that does not exits, there is nothing to fuzzy match with
    # so create the folder with the given string and return the string as a match
    # can not do more in this situation
    if path.exists(work_dir):
        return get_close_matches(string, next(walk(work_dir))[1], n=1, cutoff=cutoff)[0]
    create_folder(string, root = work_dir)
    return string

def gen_filename(size=20, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    '''
    Generate a Random String with length of 20 chars
    '''
    return ''.join(random.choice(chars) for _ in range(size))

## 
@omni.task
def handler(**opts):
    '''
    the main handler and entry point of the OMNI Downloader
    opts are kw-arguments which gets translated into Object arguments.
    each Object represents a Video that needs to be downloaded.
    '''

    # list to store all video-objects in
    videos = []

    # The HTML Form always sends a vid (VideoID) or pid (PlaylistID)
    #  So there is sth fishy going on if both are empty
    if 'vid' in opts:
        # create Video object for the ID
        videos.append(Video(id = opts['vid'], source_title = get_title_from_id(opts['vid']), **opts))
    elif 'pid' in opts:
        # get all VideoIDs from all Videos in a Playlist and create Video objects foer every ID
        for video in get_ids_from_pl(opts['pid'], **opts):
            videos.append(video)
    else:
        print('That escalated quickly ...')
        exit()

    # download every Video Object
    for video in videos:
        if video.debug: print(video.__dict__)
        video.download()

@omni.task
def download(**opts):
    if opts['debug']: print('start dl: {}'.format(opts['video_title']))
    if not opts['simulate']:
        # download
        # note that URL get passed as a list for youtube-dl to work
        youtube_dl.YoutubeDL(opts['dl_opts']).download([opts['url'],])
        # TODO
        # Idea: As the DL will take a moment, and so do ytie
        #  might be worth to kick off the dl in a seperate task, then run ytie and then wait until the dl has finished
        #  by checking the task state untill FINISHED
        #  there comes sth in mind with .state or .ready
        # ytie here
        # create images
        # file tags here
        # move the downloaded file to the desired place as defined in 'path'
        move(path.join(config['download_root'], opts['filename'] + '.mp3'), path.join(opts['path'], opts['filename'] + '.mp3'))
        # add the file to the db
        database.add_file(db, **opts)
    if opts['debug']: print('finish dl: {} - simulated: {}'.format(opts['video_title'], opts['simulate']))

#def load(url_path):
#    """ task to load a video and convert it into mp3 """
#    # declare defaults
#    # declare empty list to store Filenames in from the Download Hook
#    filenames = []
#    # switch to activate/deactivate playlist download (False)
#    sw_list = False
#    # default filename pattern used by ydl (videotitle.ext)
#    file_name_pattern = '%(title)s.%(ext)s'
#    # default setting for debuging (False)
#    debug = False
#    # set the folder to a default (False)
#    folder = False
#    # set the folder security switch to a deafult (False)
#    sw_new_folder = False
#
#    def ydl_filename_hook(dl_process):
#        """ youtube_dl filename-hook to get the filename from the downloader """
#        name = dl_process['filename'].rsplit('.', 1)[0].rsplit('/', 1)[1]
#        if name not in filenames:
#            filenames.append(name)
#
#    # build path to store files in as unicode so that youtube-dl is not complaining
#    file_path_root = '/tmp/omni_convert/'
#
#    # define a dict with options for youtube_dl
#    ydl_options = {
#        'format': 'bestaudio/best',
#        'postprocessors': [{
#            'key': 'FFmpegExtractAudio',
#            'preferredcodec': 'mp3',
#            'preferredquality': '320',
#            }],
#        'progress_hooks': [ydl_filename_hook],
#        'noplaylist': 'True',
#        'quiet': 'true',
#        }
#
#    # extract the url and options from url_path
#    #   (url_path is a list with one entry which is a unicode)
#    url = [str(url_path[0])[1:].split('::')[0]]
#    values = str(url_path[0])[1:].split('::')[1:]
#    # compile regex-pattern to detect folder-option
#    regex_folder = re.compile('folder=.*')
#
#    # process the options if there are any
#    for option in values:
#        if option == 'nodl':
#            # set option to skip the download (dry-run)
#            ydl_options.update({'skip_download' : 'true'})
#        elif regex_folder.match(option):
#            # set the plex-folder we want to store in later
#            # this value gets passed to the ytie task, it is not used in this task
#            if debug: print 'DEBUG :: option -> {}'.format(option)
#            folder = option.split('=')[1].replace('_', ' ')
#        elif option == 'new':
#            sw_new_folder = True
#        elif option == 'list':
#            # enable download of a whole playlist
#            sw_list = True
#            file_name_pattern = '%(title)s__%(playlist_title)s.%(ext)s'
#            ydl_options.pop('noplaylist', None)
#        elif option == 'debug':
#            # enable debug
#            debug = True
#            ydl_options.pop('quiet', None)
#            ydl_options.update({'verbose' : 'true'})
#        else:
#            print 'ERROR :: invalid option:\t{}'.format(option)
#
#    # build the filename pattern and path we store the files at ...
#    file_path = unicode(file_path_root + file_name_pattern)
#    # ... and add it to our ydl_options
#    ydl_options.update({'outtmpl' : file_path})
#    if debug: print 'DEBUG ::\nurlpath\t{}\nurl\t{}\noptions\t{}\nlistsw\t{}\nfolder\t{}\nnew folder\t{}\nydl_opt\t{}'.format(url_path, url, values, sw_list, folder, sw_new_folder, ydl_options)
#    # download
#    with youtube_dl.YoutubeDL(ydl_options) as ydl:
#        ydl.download(url)
#
#    for filename in filenames:
#        # build our tuple to pass it to the next task
#        arguments = (filename, file_path_root, sw_list, debug, folder, sw_new_folder)
#        if debug: print 'DEBUG :: starting task with\t{}'.format(arguments)
#        load.s(arguments)
#
#@TASK_YTIE.task
#def ytie(arguments):
#    """
#    this defines a task which uses the filename from the previous task
#    and performs YTIE operations on it, renames the file acordingly and moves
#    it to the right position
#    """
#    import subprocess
#
#    # collect our arguments
#    filename, file_path, sw_list, debug, folder, sw_new_folder = arguments
#
#    if debug: print 'DEBUG ::\nfile\t{}\npath\t{}\nlistsw\t{}\nfolder\t{}\nnew folder\t{}'.format(filename, file_path, sw_list, folder, sw_new_folder)
#
#    # current year, month and KW for path and tag building
#    date_week = datetime.datetime.today().strftime("%W")
#    date_year = datetime.datetime.today().strftime("%Y")
#    date_month = datetime.datetime.today().strftime("%m")
#
#    # define the root path where plex stores the file
#    plex_path_root = '/store/omni_convert/'
#
#    # get uid and gid of user 'plex'
#    uid = pwd.getpwnam("plex").pw_uid
#    gid = grp.getgrnam("plex").gr_gid
#
#    # process the folder and sw_list switch
#    if folder:
#        # if we got passed a foldername, it is used as albumartist/album, so that the paths got build correctly to store and it gets created if it doe not exists
#        #  - if the switch sw_new_folder == True, then we just using the passed strings as foldernames
#        #  - if the switch sw_new_folder == Fasle, then we do a check on the existing folders and find the closest match and use the match as albumartist/album
#        #      so it is ensured that typos are not passed any further
#        #  - we can handle the follwoing syntax in folder: albumartist/album & albumartist (case 2 sets album = year-kw)
#        #  - modify cutoff= value to set how close foldername has to match an existing one (lower means less equality) - default = 0.6
#        try:
#            tag_albumartist, tag_album = folder.split('/')
#        except ValueError:
#            # catch situation where there is more than 1 '/' in folder
#            if len(folder.split('/')) > 1:
#                tag_albumartist = folder.split('/')[0]
#                tag_album = folder.split('/')[1]
#            else:
#                tag_albumartist = folder
#                tag_album = date_year + '-' + date_week
#
#        # catch the case folder is sth like 'albumaritst/' where album is empty
#        if not tag_album:
#            tag_album = date_year + '-' + date_week
#
#        if debug: print 'DEBUG :: albumartist & album before close_match \nalbumartist\t{}\nalbum\t{}'.format(tag_albumartist, tag_album)
#
#        # if we got folder passed, but not sw_new_folder,
#        #  than make close_match on albumartist from folders under plex_root
#        #  than male close match on album from folders under plex_root/albumartist
#        if not sw_new_folder:
#            try:
#                tag_albumartist = get_close_matches(tag_albumartist, next(os.walk(plex_path_root))[1], n=1, cutoff=0.1)[0]
#            except IndexError:
#                tag_albumartist = 'drunk idiot'
#
#            try:
#                tag_album = get_close_matches(tag_album, next(os.walk(plex_path_root + tag_albumartist))[1], n=1, cutoff=0.1)[0]
#            except IndexError:
#                tag_album = 'go home'
#
#            if debug: print 'DEBUG :: albumartist & album after close_match\nalbumartist\t{}\nalbum\t{}'.format(tag_albumartist, tag_album)
#    else:
#        tag_albumartist = date_year + '-' + date_month
#        tag_album = date_year + '-' + date_week
#
#    if sw_list:
#        # if we load a playlist, use the list name as album and overwrite things from folder
#        try:
#            if isinstance(filename, unicode):
#                filename = unidecode(filename)
#            tag_album = str(filename.split('__')[1]) # set the playlist name as album
#        except IndexError:
#            print 'ERROR :: can not get playlistname without any loaded files'
#            tag_album = 'no-files-loaded'
#        # if folder was not set, then define the albumartist as playlists
#        if not folder:
#            tag_albumartist = 'playlists'
#
#    if debug: print 'DEBUG :: final albumartist & album \nalbumartist\t{}\nalbum\t{}'.format(tag_albumartist, tag_album)
#
#    # get rid of unicode characters if we have any and rename the loaded file
#    if isinstance(filename, unicode):
#        unifree_filename = unidecode(filename)
#        os.rename(file_path + filename + '.mp3', file_path + unifree_filename + '.mp3')
#        filename = unifree_filename
#    ytie_cmd = subprocess.Popen('java -jar /opt/omni_converter/YTIE/ExtractTitleArtist.jar \
#               -use /opt/omni_converter/YTIE/model/ ' + \
#               '"' + filename.split('__')[0] + '"', shell=True, stdout=subprocess.PIPE)
#    for line in ytie_cmd.stdout:
#        # parse the YTIE output and catch the cases where YTIE fails to detect things,
#        #  so that we do not end in empty filenames/tags
#        if 'Artists' in line:
#            try:
#                tag_artist = line.split(': ')[1].rstrip()
#            except IndexError:
#                tag_artist = 'Unknown Artist'
#
#        elif 'Title' in line:
#            try:
#                tag_title = line.split(': ')[1].rstrip()
#            except IndexError:
#                tag_title = 'Unknown Title'
#
#        elif 'Remix' in line:
#            try:
#                tag_rmx = line.split(': ')[1].rstrip()
#            except IndexError:
#                tag_rmx = False
#            if tag_rmx:
#                tag_title = tag_title + '(' + tag_rmx + ')'
#
#    # build the old filename for easier reference
#    file_old = file_path + filename + '.mp3'
#
#    # open file, decide if we load a MIX or not, depending on the track length and write mp3-tags
#    audiofile = eyed3.load(file_old)
#    if not sw_list and audiofile.info.time_secs >= 1200:
#        # if we are not loading a list and the song is longer than 20min, mark the album with ' [MIX]'
#        if debug: print 'DEBUG :: Track length: {}'.format(audiofile.info.time_secs)
#        tag_album = tag_album + ' [MIX]'
#
#    audiofile.tag.artist = unicode(tag_artist)
#    audiofile.tag.title = unicode(tag_title)
#    audiofile.tag.album = unicode(tag_album)
#    audiofile.tag.album_artist = unicode(tag_albumartist)
#    audiofile.tag.save()
#
#    # build paths to plex library for easier reference
#    plex_path_artist = plex_path_root + tag_albumartist + '/'
#    plex_path = plex_path_artist + tag_album + '/'
#
#    # create plex folders if not exist
#    if not os.path.exists(plex_path):
#        if debug: print 'DEBUG :: create new plex-dir {}'.format(plex_path)
#        os.makedirs(plex_path)
#        # set perminssions on dir
#        try:
#            os.chown(plex_path, uid, gid)
#            os.chmod(plex_path, 0770)
#        except OSError:
#            print 'ERROR :: error while set permission on {}'.format(plex_path)
#
#    # build the new file name for easier reference
#    file_new = plex_path + tag_artist + ' - ' + tag_title + '.mp3'
#
#    ## ALBUM cover generator
#    # generate text for album cover
#    cover_album_text = tag_album
#    text_length = len(cover_album_text)
#    text_max_length = 20
#    # if text is longer than text_max_length, then strip it
#    if text_length >= text_max_length:
#        cover_album_text = cover_album_text[:text_max_length]
#        text_length = len(cover_album_text)
#    # if last char is space, strip it off
#    if cover_album_text[-1] == ' ':
#        cover_album_text = cover_album_text[:-1]
#        text_length = len(cover_album_text)
#
#    # build the name of the cover-jpg and check if it already exists. Skip if true
#    album_cover = plex_path + 'poster.jpg'
#
#    # create album cover, if it dos not already exists
#    if not os.path.exists(album_cover):
#        # open image
#        cover = Image.open('res/black.jpg')
#        # get size of our template image
#        image_x, image_y = cover.size
#        # enable drawing
#        draw = ImageDraw.Draw(cover)
#        # calc the font size depending on the image size and ammount of characters
#        font_size = (2 * image_y) / text_length
#        # calc the y_offset for the text, depending on the font size
#        text_offset = (image_x - font_size) / 2
#        # set font type and size
#        font = ImageFont.truetype("UbuntuMono-B.ttf", font_size)
#        # be picasso
#        draw.text((0, text_offset), cover_album_text, (255, 255, 255), font=font)
#        # save image
#        cover.save(album_cover)
#    elif debug:
#        font_size = 'not calculated'
#        image_x = 'not calculated'
#        image_y = 'not calculated'
#        text_offset = 'not calculated'
#
#    if debug: print 'DEBUG ::\nALBUM-Cover\ntag artist:\t{}\ntag title:\t{}\ntag album:\t{}\ntag album art.:\t{}\nfile cover:\t{}\ncover text:\t{}\ncover text len:\t{}\ncover text size:\t{}\ncover size x:\t{}\ncover size y:\t{}\ncover offset y:\t{}\n'.format(tag_artist, tag_title, tag_album, tag_albumartist, album_cover, cover_album_text, text_length, font_size, image_x, image_y, text_offset)
#
#
#    ## ARTIST cover generator
#    # generate text for artist cover
#    cover_artist_text = tag_albumartist
#    text_length = len(cover_artist_text)
#    # if text is longer than text_max_length, then strip it
#    if text_length >= text_max_length:
#        cover_artist_text = cover_artist_text[:text_max_length]
#        text_length = len(cover_artist_text)
#    # if last char is space, strip it off
#    if cover_artist_text[-1] == ' ':
#        cover_artist_text = cover_artist_text[:-1]
#        text_length = len(cover_artist_text)
#
#    # build the name of the cover-jpg and check if it already exists. Skip if true
#    artist_cover = plex_path_artist + 'poster.jpg'
#
#    # create artist cover, if it dos not already exists
#    if not os.path.exists(artist_cover):
#        # open image
#        cover = Image.open('res/black.jpg')
#        # get size of our template image
#        image_x, image_y = cover.size
#        # enable drawing
#        draw = ImageDraw.Draw(cover)
#        # calc the font size depending on the image size and ammount of characters
#        font_size = (2 * image_y) / text_length
#        # calc the y_offset for the text, depending on the font size
#        text_offset = (image_x - font_size) / 2
#        # set font type and size
#        font = ImageFont.truetype("UbuntuMono-B.ttf", font_size)
#        # be picasso
#        draw.text((0, text_offset), cover_artist_text, (255, 255, 255), font=font)
#        # save image
#        cover.save(artist_cover)
#    elif debug:
#        font_size = 'not calculated'
#        image_x = 'not calculated'
#        image_y = 'not calculated'
#        text_offset = 'not calculated'
#
#    if debug: print 'DEBUG ::\nARTIST-Cover\ntag artist:\t{}\ntag title:\t{}\ntag album:\t{}\ntag album art.:\t{}\nfile cover:\t{}\ncover text:\t{}\ncover text len:\t{}\ncover text size:\t{}\ncover size x:\t{}\ncover size y:\t{}\ncover offset y:\t{}\n'.format(tag_artist, tag_title, tag_album, tag_albumartist, artist_cover, cover_artist_text, text_length, font_size, image_x, image_y, text_offset)
#
#    if debug: print 'DEBUG :: moving file\t{} -->> {}'.format(file_old, file_new)
#    # move the file and set the permissions
#    try:
#        os.rename(file_old, file_new)
#        os.chown(file_new, uid, gid)
#        os.chmod(file_new, 0660)
#    except OSError:
#        print 'ERROR :: error while moving file or setting permissions'

