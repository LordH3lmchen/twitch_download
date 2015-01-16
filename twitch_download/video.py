__author__ = 'Flo'


class VideoInfo(object):
    """
    Objekte dieses Typs enthalten diverse Informationen zu einem Broadcast oder Video.
    """

    def __init__(self,
                 stream_name='',
                 channel_category='',
                 channel_name='',
                 title='',
                 mature=False,
                 meta_game='no_meta_game',
                 start_time='',
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
        if quality is None:
            return None
        else:
            return self._video_file_urls[quality]

    def get_available_qualities(self):
        return self._video_file_urls.keys()