# pydaap - a Python-based daap media sharing library
# Copyright (C) 2010 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.

# googlebackend.py
#
#
# Google Music backend.
#
# This is really dodgy, on many levels:
#
# This listing is not accurate - we can race between getting the 
# filelist from the filesystem and returning it to the user.
#

import os
import time
from itertools import count
import libdaap

import ConfigParser
from clientlogin import ClientLogin
from urllib2 import urlopen, Request
from urllib2 import HTTPError
from urllib import urlencode
import json

class MusicException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.msg = message

class MusicURL:
    BASE_URL = 'https://www.googleapis.com/sj/v1beta1/'

    @staticmethod
    def tracks():
        return MusicURL.BASE_URL+'tracks'

    @staticmethod
    def playlists():
        return MusicURL.BASE_URL+'playlists'

    @staticmethod
    def play(songid):
        return 'https://music.google.com/music/play?songid=%s&targetkbps=256&pt=e' % songid

        # Android client uses this, but it requires X-Device-ID header
        #return 'https://android.clients.google.com/music/mplay?songid=%s&targetkbps=128&pt=e' % songid

    @staticmethod
    def auth():
        return 'https://music.google.com/music/listen?u=0'

class GTrack:
    def __init__(self, client, data):
        self.client = client

        self.uuid = data['id'] #if this isn't set, we should fail
        self.title = 'Untitled'
        self.artist = 'Unknown Artist'
        self.composer = ''
        self.album = 'Unknown Album'
        self.albumArtist = 'Unknown Album Artist'
        self.year = 0
        self.comment = ''
        self.trackNumber = 0
        self.genre = ''
        self.beatsPerMinute = 0
        self.durationMillis = 0
        self.totalTrackCount = 0
        self.discNumber = 0
        self.totalDiscCount = 0
        self.rating = 0
        self.deleted = False

        if 'title' in data:
            self.title = data['title']
        if 'artist' in data:
            self.artist = data['artist']
        if 'composer' in data:
            self.composer = data['composer']
        if 'album' in data:
            self.album = data['album']
        if 'albumArtist' in data:
            self.albumArtist = data['albumArtist']
        if 'year' in data:
            self.year = int(data['year'])
        if 'comment' in data:
            self.comment = data['comment']
        if 'trackNumber' in data:
            self.trackNumber = int(data['trackNumber'])
        if 'genre' in data:
            self.genre = data['genre']
        if 'beatsPerMinute' in data:
            self.beatsPerMinute = int(data['beatsPerMinute'])
        if 'durationMillis' in data:
            self.durationMillis = int(data['durationMillis'])
        if 'totalTrackCount' in data:
            self.trackCount = int(data['totalTrackCount'])
        if 'discNumber' in data:
            self.discNumber = int(data['discNumber'])
        if 'totalDiscCount' in data:
            self.discCount = int(data['totalDiscCount'])
        if 'rating' in data:
            self.rating = int(data['rating'])
        if 'deleted' in data:
            self.deleted = bool(data['deleted'])

        self.client.tracks.append(self)

class GTrackList:
    def __init__(self, client, data):
        self.client = client
        for track in data['data']['items']:
            self.client.parse_item(track)

class GMusic:
    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read('config.ini')
        self.auth_token = None
        self.auth_cookie = None

        self.tracks = []

    def _make_request(self, url, data='', headers={}):
        data = urlencode(data)
        if data == '':
            data = None
        else:
            data = data.encode('utf8')

        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'application/json'
        headers['Authorization'] = 'GoogleLogin auth=%s' % self.auth_token

        req = Request(url, data, headers)
        err = None

        try:
            resp_obj = urlopen(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        resp = resp_obj.read()
        resp_obj.close()
        return None, unicode(resp, encoding='utf8')

    def _make_track_request(self, url, headers={}):
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'application/json'
        headers['Authorization'] = 'GoogleLogin auth=%s' % self.auth_token
        headers['Cookie'] = 'sjsaid=%s' % self.auth_cookie

        req = Request(url, None, headers)
        err = None

        try:
            resp_obj = urlopen(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        resp = resp_obj.read()
        resp_obj.close()
        return None, unicode(resp, encoding='utf8')

    def _make_audio_request(self, url):
        headers = {}
        headers['Context-Type'] = 'audio/mp3'
        headers['Authorization'] = 'GoogleLogin auth=%s' % self.auth_token
        headers['Cookie'] = 'sjsaid=%s' % self.auth_cookie

        req = Request(url, None, headers)
        err = None

        try:
            resp_obj = urlopen(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        return None, resp_obj

    def parse_item(self, jsobj):
        if 'kind' not in jsobj:
            raise "Invalid JSON object"

        if jsobj['kind'] == 'sj#track':
            return GTrack(self, jsobj)
        elif jsobj['kind'] == 'sj#trackList':
            return GTrackList(self, jsobj)
        else:
            raise MusicException("Unsupported object type %s" % jsobj['kind'])

    def do_auth(self):
        if not self.config.has_section('Auth'):
            self.config.add_section('Auth')
        if self.config.has_option('Auth', 'Token'):
            self.auth_token = self.config.get('Auth', 'Token', None)
        if self.auth_token is None:
            print('Please enter your Google username:')
            user = raw_input()
            self.config.set('Auth', 'Username', user)
            print('Please enter your password:')
            passwd = raw_input()

            loginclient = ClientLogin(user, passwd, 'sj')
            self.auth_token = loginclient.get_auth_token(True)
            self.config.set('Auth', 'Token', self.auth_token)
            with open('config.ini', 'w') as f:
                self.config.write(f)

    def get_cookie(self):
        headers = {}
        headers['Authorization'] = 'GoogleLogin auth=%s' % self.auth_token

        req = Request(MusicURL.auth(), None, headers)
        err = None

        # Normally we'd want to catch this, but at this point if it doesn't
        # work then we pretty much need to die
        resp_obj = urlopen(req)
        info = resp_obj.info()

        cookies = dict(s.split(';', 1)[0].split('=', 1) for s in info.getheaders('Set-Cookie'))
        if 'sjsaid' not in cookies:
            raise MusicException("Didn't receive authentication cookie")
        self.auth_cookie = cookies['sjsaid']

    def get_tracks(self):
        if self.auth_token is None:
            self.do_auth()
        if self.auth_cookie is None:
            self.get_cookie()

        err, resp = self._make_request(MusicURL.tracks())
        if not err is None:
            print 'Error Code %d' % err
            raise MusicException("Error Code %d" % err)

        jsdata = json.loads(resp)
        self.parse_item(jsdata)

        return self.tracks

    def get_audio_track(self, uuid):
        url = MusicURL.play(uuid)

        err, resp = self._make_track_request(url)
        if not err is None:
            print 'Error Code %d' % err
            raise MusicException("Error Code %d" % err)

        jsdata = json.loads(resp)
        err, resp = self._make_audio_request(jsdata['url'])
        if not err is None:
            print 'Error Code %d' % err
            raise MusicException("Error Code %d" % err)

        length = resp.info().getheaders('Content-Length')
        return resp, int(length[0])


class Backend(object):
    def __init__(self, auth=None):
        self.client = GMusic()
        if auth:
            self.client.auth_token = auth
        self.items = dict()
        self.itemuuids = dict()
        self.build_files()

    def get_name(self):
        try:
            username = self.client.config.get('Auth', 'Username')
            return "%s's Google Music" % username
        except:
            return 'Google Music'

    def build_files(self):
        i = 0
        for t in self.client.get_tracks():
            item = dict()
            item['dmap.itemid'] = i
            item['dmap.itemname'] = t.title
            item['dmap.persistentid'] = i
            item['daap.songalbum'] = t.album
            item['daap.songartist'] = t.artist
            item['daap.songdiscnumber'] = t.discNumber
            item['daap.songformat'] = 'mp3'
            item['daap.songtime'] = t.durationMillis
            item['daap.songtracknumber'] = t.trackNumber
            item['daap.songuserrating'] = t.rating
            item['daap.songyear'] = t.year
            item['valid'] = not t.deleted
            item['revision'] = 2
            item['com.apple.itunes.mediakind'] = 1

            self.items[i] = item
            self.itemuuids[i] = t.uuid
            i += 1

    def get_revision(self, session, old_revision, request):
        return 2
        #if old_revision == 1:
        #    return 2
        while True:
            time.sleep(3600)

    def get_playlists(self):
        return dict()

    def get_items(self, playlist_id=None):
        return self.items

    def get_file(self, itemid, generation, ext, session, request_path_func,
                 offset=0, chunk=None):
        uuid = self.itemuuids[itemid]
        audio_fd, length = self.client.get_audio_track(uuid)

        return audio_fd, length, None

