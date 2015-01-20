import re

import requests

from twitch_download.video import VideoInfo


__author__ = 'flo'


BASE_URL = 'https://api.twitch.tv'


def get_video_info(id_):
    """
    Eine Factory-Methode die ein VideoInfo Obkjekt aus einer Twitch URL generiert.
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
    bcast_json = r.json()
    bcast_info_json = r_info.json()
    video_info = VideoInfo(bcast_info_json['title'],
                           'Gaming',
                           bcast_info_json['channel']['display_name'],
                           bcast_info_json['title'],
                           'unknown',
                           bcast_info_json['game'],
                           bcast_info_json['recorded_at'],
                           bcast_info_json['url'])  # add Description

    for quality in bcast_json['chunks']:
        for part in bcast_json['chunks'][quality]:
            video_info.append_video_file_url(quality, part['url'])
    return video_info


def get_highest_quality(video_info):
    qualities_desc = ('live', '720p', '480p', '360p', '240p')
    for quality in qualities_desc:
        if quality in video_info.get_available_qualities():
            return quality
        else:
            return None


class TwitchApiError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)