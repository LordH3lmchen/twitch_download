#!/usr/bin/env python3
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

            2014-11-03:
                Twitch API changed. This script uses know api.twitch.tv instead of api.justin.tv

            2014-11-04:
                The script works now on OS X (Apple)
                Fixed Config Initialization Error

            2014-11-09:
                Small improvements and some bugfixes

'''

import os
import sys
import string
import configparser
import subprocess
from optparse import OptionParser
import requests
import re
import twitch

__author__ = 'Flo'

FFMPEG_BIN = os.getcwd() + '\\ffmpeg.exe'



def safe_filename(title):
    """ returns a valid filename for the 'title' string """
    #title = title.encode('ascii', 'ignore')
    allowed = "-_.() " + string.ascii_letters + string.digits + '\\' + '/'
    safeTitle = "".join([c for c in title if c in allowed])
    return safeTitle.replace(' ', '_')


def download_file(url, fullFilePath, cur_part, num_parts):
    CS = 1024
    cur_length = 0

    # r = requests.head(url)
    r = requests.get(url, stream=True, timeout=(3.05, 27))
    file_size = int(r.headers['Content-Length']) / float(pow(1024, 2))
    if r.headers['Content-Type'] != 'video/x-flv':
        raise Exception("Incorrect Content-Type ({0}) for {1}".format(r.headers['Content-Type'], url))


    with open(fullFilePath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=CS):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
                cur_length += CS
                sys.stdout.write("\rDownloading {0}/{1}: {2:.2f}/{3:.2f}MB ({4:.1f}%)".format(cur_part, num_parts, cur_length / float(pow(1024, 2)), file_size, ((cur_length / float(pow(1024, 2))) / file_size) * 100))
    f.close()
    print("...complete")


def remove_latest_videofile(part_filename):
    filelist = []
    for filename in os.listdir(os.path.dirname(part_filename)):
        if (filename.endswith('.flv')) and (filename.startswith(os.path.basename(part_filename))):
            filelist.append(filename)
    if len(filelist)>0:
        print('incomplete download found, deleting incomplete file ' + filelist[-1])
        os.remove(os.path.dirname(part_filename) + '\\' + filelist[-1])


def download_broadcast(broadcast_info, filename, quality=None):
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

    if quality == None:
        quality = twitch.get_highest_quality(broadcast_info)
        print('No quality specified, downloading ' + quality + '-quality.')

    if quality in broadcast_info.get_available_qualities():
        tmp_video_file_urls = broadcast_info.get_video_file_urls(quality)
    else:
        print(quality + "-quality isn't available\n")   # Some broadcasts are not available in every quality
        print("Available qualities are ")
        for available_quality in broadcast_info.get_available_qualities():
            print("\t" + available_quality)

    for nr, video_file_url in enumerate(tmp_video_file_urls):
        ext = os.path.splitext(video_file_url)[1]
        part_filename = "{0}_{1:0>2}{2}".format(filename, nr, ext)
        f.write('file \'' + part_filename + '\'\n')
        if os.path.exists(part_filename):
            print(os.path.basename(part_filename) + ' already loaded!')
        else:
            download_file(video_file_url, part_filename, nr+1, len(tmp_video_file_urls))

    f.close()
    subprocess.check_call([FFMPEG_BIN, '-f', 'concat', '-i', filename + '_filelist.tmp', '-c', 'copy', filename + '.mp4'])
    os.remove(filename + '_filelist.tmp')


def print_help():
    print("In this interactive mode you can enter the Stream id or the URL to the past broadcast")
    print("Append the quality after the specication of the stream.\n"
          "The best quality available will be selected by default.\n"
          "Examples:\n"
          "\thttp://www.twitch.tv/esltv_sc2/b/585041281 720p\n"
          "\thttp://www.twitch.tv/esltv_sc2/b/585041281\n"
          "\t585041281\n"
          "\t585041281 240p\n"
          "\n"
          "Available qualities: "
          "240p, 360p, 480p, 720p, source\n")
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
                interactive_input = interactive_input.split()
                broadcast_info = twitch.get_video_info(interactive_input[0])

        except twitch.TwitchApiError as e:
            print('TwitchApiError occured: ', e.message)
            continue
        if broadcast_info.meta_game == None:    # Es gibnt Broadcasts ohne meta_game angabe
            broadcast_info.meta_game = 'no_meta_game' #Ersetze None durch 'no_meta_game' um einen Fehler im filename zu vermeiden.
        filename = download_folder + safe_filename("/" + broadcast_info.meta_game + "/" + broadcast_info.channel_name + "/" + broadcast_info.title + '_' + broadcast_info.start_time)
        if len(interactive_input) == 2:
            filename = filename + interactive_input[1]
            download_broadcast(broadcast_info, filename, interactive_input[1])
        elif len(interactive_input) == 1:
            download_broadcast(broadcast_info, filename)
        else:
            print("invalid input! Specify URL, StreamID with optional Quality\n")
            print_help()


if __name__=="__main__":

    #create cfg-file if needed.
    config = configparser.RawConfigParser()
    if os.path.exists('twitch_download.cfg') == False:
        print('config_file not found!')
        download_folder = ''
        FFMPEG_BIN = ''
        while len(download_folder) == 0:
            download_folder = input('specify download folder: ')
            if os.path.exists(download_folder) == False:
                print('invalid download directory!')
                download_folder = ''
        while len(FFMPEG_BIN) == 0:
            FFMPEG_BIN = input('specifiy the \"ffmpeg\" - binary (Full PATH): ')
            FFMPEG_BIN = FFMPEG_BIN
            if os.path.exists(FFMPEG_BIN) == False:
                print('ffmpeg not found!')
                FFMPEG_BIN = ''
        config.set('DEFAULT', 'download_folder', download_folder)
        config.set('DEFAULT', 'ffmpeg_bin', FFMPEG_BIN)
        with open('twitch_download.cfg', 'w') as configfile:
            config.write(configfile)
    else:
        config.read('twitch_download.cfg')
        try:
            download_folder = config.get('DEFAULT', 'download_folder')
            FFMPEG_BIN = config.get('DEFAULT', 'ffmpeg_bin')
        except (KeyError, configparser.NoOptionError) as e:
            print('Invalid  config-file:\n\n' + str(e) + '\n\nFix the twitch_download.cfg or delete it to generate a new one.')
            exit();
    usage = "usage: %prog [TwitchBroadcastId ... ]"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    if len(args)==0:
        interactive_mode()
    else:
        broadcastURLs = args
        for broadcastURL in broadcastURLs:
            try:
                broadcast_info = twitch.get_video_info(broadcastURL)
            except twitch.TwitchApiError as e:
                print('TwitchApiError occured', e.message)
                continue
            filename =  download_folder + safe_filename("/" + broadcast_info.meta_game + "/" + broadcast_info.channel_name + "/" + broadcast_info.title + '_' + broadcast_info.start_time)
            download_broadcast(broadcast_info, filename)
