# filebackend.py
#
# Miro - an RSS based video player application
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

#
# Dumb file backend.
#
# This is really dodgy, on many levels:
#
# This listing is not accurate - we can race between getting the 
# filelist from the filesystem and returning it to the user.
#

import os
from itertools import count

supported_exts = ['.mp3', '.mp4']

class Backend(object):
    def __init__(self, path, ext=supported_exts):
        self.path = path
        self.ext = ext
        self.items = dict()
        self.itempaths = dict()
        self.build_files()

    def build_files(self):
        for c, entry in zip(count(1), os.listdir(self.path)):
            nam, ext = os.path.splitext(entry)
            path = os.path.join(self.path, entry)
            if (os.path.isfile(os.path.join(self.path, entry)) and
              ext in self.ext):
                self.items[c] = [('miid', c), ('minm', nam), ('asfm', ext)]
                self.itempaths[c] = path

    def get_playlists(self):
        return []

    def get_items(self, playlist_id=None):
        return self.items

    def get_filepath(self, itemid):
        return self.itempaths[itemid]
