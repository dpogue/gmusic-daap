# filebackend.py
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
                self.items[c] = [('minm', nam), ('asfm', ext)]
                self.itempaths[c] = path

    def get_items(self):
        return self.items

    def get_filepath(self, itemid):
        return self.itempaths[itemid]
