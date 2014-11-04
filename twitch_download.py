#!/usr/bin/env python
# encoding: utf-8
'''
twitch_download -- small commandline tool to download Past Broadcasts from Twitch.

downloads and converts Broadcasts from Twitch


@author:     Florian Trabauer

@copyright:  2014 Florian Trabauer. All rights reserved.

@license:    GPLv2

@contact:    florian@trabauer.com
@deffield    updated: 2014-08-11
                initial version
            2014-08-18:
                div. Code reorgansisiert
                Fehler behoben. Es gibt PastBroadcasts ohne meta_game.
                Diese werden als no_meta_game deklariert
            2014-08-19:
                Statt einer Json Struktur wird ein VideoInfo Objekt erzeugt das die relevanten Informationen aus der
                 Justin.tv API enthält. So können auch andere APIs implementiert werden, die auch nur ein VideoInfo
                 Objekt erzeugen.

            2014-11-3:
                Twitch API changed. This script uses know api.twitch.tv instead of api.justin.tv
                Fixed Config Init Error

'''

import requests
import re
import os
import string
import configparser
import subprocess
from optparse import OptionParser


__author__ = 'Flo'

BASE_URL = 'https://api.twitch.tv'
FFMPEG_PATH = os.getcwd() + '\\ffmpeg.exe'


class Twitch(object):
    """
    Stellt Methoden zur interaktion mit Twitch bereit
    """
    @staticmethod
    def getBroadcastInfo(id_):
        """
        Eine Factory die ein VideoInfo Obkjekt aus einer Twitch URL generiert.
        """

        http_pb = re.compile('http://www.twitch.tv/\S+/b/\d+')  # PastBroadcast URL
        http_matchb = http_pb.match(id_)

        if http_matchb:
            id_ = id_.split('/')[5]
        elif id_.isdigit():
            pass
        else:
            raise TwitchApiError("Invalid stream specification: " + id_)

        pattern = '{base}/api/videos/a{id_}'
        info_pattern = '{base}/kraken/videos/a{id_}?on_site=1'
        url = pattern.format(base=BASE_URL, id_=id_)
        info_url = info_pattern.format(base=BASE_URL, id_=id_)
        r = requests.get(url)
        r_info = requests.get(info_url)

        if r_info.status_code != 200:
            raise TwitchApiError("API returned {0}".format(r_info.status_code))
        if r.status_code != 200:
            raise TwitchApiError("API returned {0}".format(r.status_code))
        bcastJson = r.json()
        bcastInfoJson = r_info.json()

        broadcast_info = VideoInfo(bcastInfoJson['title'], \
                                      'Gaming', \
                                      bcastInfoJson['channel']['display_name'], \
                                      bcastInfoJson['title'], \
                                      'unknown', \
                                      bcastInfoJson['game'], \
                                      bcastInfoJson['recorded_at'], \
                                      bcastInfoJson['url'])  # add Description

        for quality in bcastJson['chunks']:
            for part in bcastJson['chunks'][quality]:
                broadcast_info.append_video_file_url(quality, part['url'])


        return  broadcast_info


class TwitchApiError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class VideoInfo(object):
    """
    Objekte dieses Typs enthalten diverse Informationen zu einem Broadcast oder Video.
    """

    def __init__(self, \
                 stream_name='', \
                 channel_category='', \
                 channel_name='', \
                 title='', \
                 mature=False, \
                 meta_game='no_meta_game', \
                 start_time='', \
                 link_url=''):

        self.stream_name = stream_name
        self.channel_category = channel_category
        self.channel_name = channel_name
        self.title = title
        self.mature = mature
        self.meta_game = meta_game
        self.start_time = start_time
        self.link_url = link_url
        self.file_size = []
        self.start_timestamp = []
        self._video_file_urls = {}

    def append_video_file_url(self, quality, url):
        if quality in self._video_file_urls:
            self._video_file_urls.get(quality).append(url)
        else:
            self._video_file_urls.update({quality: [url]})

    def get_video_file_urls(self, quality):
        return self._video_file_urls[quality]

    def get_available_qualities(self):
        return self._video_file_urls.keys()



def safe_filename(title):
    """ returns a valid filename for the 'title' string """
    #title = title.encode('ascii', 'ignore')
    allowed = "-_.() " + string.ascii_letters + string.digits + '\\' + '/'
    safeTitle = "".join([c for c in title if c in allowed])
    return safeTitle.replace(' ', '_')


def download_file(url, fullFilePath):
    print("downloading {0}".format(os.path.basename(fullFilePath)))


    CS = 1048576
    done = 0
    r = requests.get(url, stream=True)
    with open(fullFilePath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=CS):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
                done += CS
                print("\r{0:>7.1f} MB".format(done/float(pow(1024,2))), end=' ')
    f.close()
    print("done\n")


def remove_latest_videofile(part_filename):
    filelist = []
    for filename in os.listdir(os.path.dirname(part_filename)):
        if (filename.endswith('.flv')) and (filename.startswith(os.path.basename(part_filename))):
            filelist.append(filename)
    if len(filelist)>0:
        print('incomplete download found, deleting incomplete file ' + filelist[-1])
        os.remove(os.path.dirname(part_filename) + '\\' + filelist[-1])


def download_broadcast(broadcast_info, filename):
    """ download all video parts for broadcast 'id_' """
    # erstelle zielordner falls noetig
    filename = os.path.abspath(filename)
    if os.path.exists(os.path.dirname(filename)) == False:
        os.makedirs(os.path.dirname(filename))
    f = open(filename + '_filelist.tmp', 'w')  # fileliste fuer ffmpeg
    if os.path.exists(filename + '.mp4'):
        print(filename + '.mp4 already downloaded')
        f.close()
        os.remove(filename + '_filelist.tmp')
        return
    remove_latest_videofile(filename)
    tmp_video_file_urls = broadcast_info.get_video_file_urls('live')
    for nr, video_file_url in enumerate(tmp_video_file_urls):
        ext = os.path.splitext(video_file_url)[1]
        part_filename = "{0}_{1:0>2}{2}".format(filename, nr, ext)
        f.write('file \'' + part_filename + '\'\n')
        if os.path.exists(part_filename):
            print(os.path.basename(part_filename) + ' already loaded!')
        else:
            download_file(video_file_url, part_filename)
    f.close()
    subprocess.check_call([FFMPEG_PATH, '-f', 'concat', '-i', filename + '_filelist.tmp', '-c', 'copy', filename + '.mp4'])
    os.remove(filename + '_filelist.tmp')


def print_help():
    print("In this interactive mode you can enter the Stream id or the URL to the past broadcast")
    print("Example: \"http://www.twitch.tv/redbullesports/b/556269222\"")
    print("This script will create the folder hierarchy <yourLibrary\<game>\<streamer> for your download.")
    print("After the download the script converts the Past Broadcast in a mp4-Video with ffmpeg")


def interactive_mode():
    print('twitch_download\n===============\n\nYou can enter StreamId\'s, help or exit')

    os.chdir(download_folder)

    while True:
        interactive_input = input('> ')

        try:
            if interactive_input == 'exit':
                exit(0)
            elif interactive_input == 'help':
                print_help()
                continue
            else:
                broadcast_info = Twitch.getBroadcastInfo(interactive_input)
        except TwitchApiError as e:
            print('TwitchApiError occured: ', e.message)
            continue
        if broadcast_info.meta_game == None:    # Es gibnt Broadcasts ohne meta_game angabe
            broadcast_info.meta_game = 'no_meta_game' #Ersetze None durch 'no_meta_game' um einen Fehler im filename zu vermeiden.
        filename = download_folder + safe_filename("/" + broadcast_info.meta_game + "/" + broadcast_info.channel_name + "/" + broadcast_info.title + '_' + broadcast_info.start_time)
        download_broadcast(broadcast_info, filename)


if __name__=="__main__":

    #create cfg-file if needed.
    config = configparser.RawConfigParser()
    if os.path.exists('twitch_download.cfg') == False:
        print('config_file not found!')
        download_folder = ''
        FFMPEG_PATH = ''
        while len(download_folder) == 0:
            download_folder = input('specify download folder: ')
            if os.path.exists(download_folder) == False:
                print('invalid download directory!')
                download_folder = ''
        while len(FFMPEG_PATH) == 0:
            FFMPEG_PATH = input('specifiy the folder that contains \"ffmpeg.exe\" : ')
            FFMPEG_PATH = FFMPEG_PATH + '/ffmpeg.exe'
            if os.path.exists(FFMPEG_PATH) == False:
                print('ffmpeg.exe not found!')
                FFMPEG_PATH = ''
        config.set('DEFAULT', 'download_folder', download_folder)
        config.set('DEFAULT', 'ffmpeg_path', FFMPEG_PATH)
        with open('twitch_download.cfg', 'w') as configfile:
            config.write(configfile)
    else:
        config.read('twitch_download.cfg')
        try:
            download_folder = config.get('DEFAULT', 'download_folder')
            FFMPEG_PATH = config.get('DEFAULT', 'ffmpeg_path')
        except (KeyError, configparser.NoOptionError) as e:
            print('Invalid  config-file:\n\n' + str(e) + '\n\nFix the twitch_download.cfg or delete it to generate a new one.')
            exit();
    usage = "usage: %prog [TwitchBroadcastId ... ]"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    if len(args)==0:
        interactive_mode()
    if len(args)!=1:
        print("invalid number of arguments\n Use --help option ")
    else:
        broadcastURLs = args
        for broadcastURL in broadcastURLs:
            try:
                broadcast_info = Twitch.getBroadcastInfo(broadcastURL)
            except TwitchApiError as e:
                print('TwitchApiError occured', e.message)
                continue
            filename = download_folder + "/" + safe_filename(broadcast_info[0]['meta_game'] + "/" + broadcast_info[0]['channel_name'] + "/" + broadcast_info[0]['title'] + '_' + broadcast_info[0]['start_time'])
            download_broadcast(broadcast_info, filename)
