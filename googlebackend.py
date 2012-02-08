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

    def playlists():
        return MusicURL.BASE_URL+'playlists'

    def play(songid):
        return 'https://android.clients.google.com/music/mplay?songid=%s&targetkbps=128&pt=e' % songid

class GTrack:
    def __init__(self, client, data):
        self.client = client
        self.uuid = data['id']
        self.title = data['title']
        self.artist = data['artist']
        self.album = data['album']
        self.albumArtist = data['albumArtist']
        self.year = int(data['year'])
        self.rating = int(data['rating'])
        self.trackNumber = int(data['trackNumber'])
        self.discNumber = int(data['discNumber'])
        self.durationMillis = int(data['durationMillis'])

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

    def _make_audio_request(self, url, headers={}):
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'application/json'
        headers['Authorization'] = 'GoogleLogin auth=%s' % self.auth_token

        req = Request(url, None, headers)
        err = None

        try:
            resp_obj = urlopen(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        resp = resp_obj.read()
        resp_obj.close()
        return None, resp

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
        if self.config.has_option('Auth', 'Token'):
            self.auth_token = self.config.get('Auth', 'Token', None)
        if self.auth_token is None:
            print('Please enter your Google username:')
            user = raw_input()
            print('Please enter your password:')
            passwd = raw_input()

            loginclient = ClientLogin(user, passwd, 'sj')
            self.auth_token = loginclient.get_auth_token(True)
            if not self.config.has_section('Auth'):
                self.config.add_section('Auth')
            self.config.set('Auth', 'Token', self.auth_token)
            with open('config.ini', 'w') as f:
                self.config.write(f)

    def get_tracks(self):
        if self.auth_token is None:
            self.do_auth()

        err, resp = self._make_request(MusicURL.tracks())
        if not err is None:
            raise MusicException("Error Code %d" % err)

        jsdata = json.loads(resp)
        self.parse_item(jsdata)

        return self.tracks


class Backend(object):
    def __init__(self, auth=None):
        self.client = GMusic()
        if auth:
            self.client.auth_token = auth
        self.items = dict()
        self.itemuuids = dict()
        self.build_files()

    def get_name(self):
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
            item['valid'] = True
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
        file_obj = open(self.itemuuids[itemid], 'rb')
        file_obj.seek(offset, os.SEEK_SET)
        return file_obj, self.itemuuids[itemid]

