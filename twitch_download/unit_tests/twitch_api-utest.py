__author__ = 'Flo'

import unittest

from twitch_download import video, twitch


class MyTestCase(unittest.TestCase):
    def test_twitch_get_video_info(self):
        video_info = video.VideoInfo()
        video_info = twitch.get_video_info('http://www.twitch.tv/taketv/b/581044708')
        urls = video_info.get_video_file_urls('live')

        print('Available Qualities:')
        for quality in video_info.get_available_qualities():
            print(quality)

        print('File URLs for "' + video_info.title + '" on ' + video_info.channel_name)
        for url in urls:
            print(url)

        print('Highest Quality: ' + twitch.get_highest_quality(video_info))


if __name__ == '__main__':
    unittest.main()
