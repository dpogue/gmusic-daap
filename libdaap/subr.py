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

# subr.py

import os
import stat
import struct
import urllib
from const import *

# XXX calcsize()?  We need to do some overriding however.
fmts = {
    DMAP_TYPE_LIST: ('0s', 0),
    DMAP_TYPE_BYTE: ('b', 1),
    DMAP_TYPE_UBYTE: ('B', 1),
    DMAP_TYPE_SHORT: ('h', 2),
    DMAP_TYPE_USHORT: ('H', 2),
    DMAP_TYPE_INT: ('i', 4),
    DMAP_TYPE_UINT: ('I', 4),
    DMAP_TYPE_LONG: ('q', 8),
    DMAP_TYPE_ULONG: ('Q', 8),
    DMAP_TYPE_DATE: ('I', 4),
    DMAP_TYPE_STRING: ('s', 0),
    DMAP_TYPE_VERSION: ('I', 4),
}

class StreamObj(object):
    """
       Data object for encoding HTTP responses.  Use once then dispose.
    """
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return str(self.data)

    # Treat this as one big block of data.
    def __iter__(self):
        yield self.data

    def __len__(self):
        return len(self.data)

    def get_rangetext(self):
        return ''

class ChunkedStreamObj(object):
    """
       Streaming object.  Use once and then you must dispose.
       XXX make this stream arbitrary things rather than file-oriented?

       Typical read pattern is to create one of these things, then
       in the write function:

       for chunk in streamobj:
           write(chunk)
    """
    DEFAULT_CHUNK_SIZE = 128 * 1024

    def __init__(self, path, start=0, end=0, chunksize=DEFAULT_CHUNK_SIZE):
        self.chunksize = chunksize
        self.path = path
        self.fileobj = open(path, 'rb')
        self.end = end
        self.filesize = os.stat(path)[stat.ST_SIZE]
        self.streamsize = self.filesize
        self.fileobj.seek(start)
        rangetext = ''
        if start and start < self.filesize:
            self.fileobj.seek(start)  
            self.streamsize = self.filesize - start
            rangetext = (str(start) + '-' + str(self.filesize) + '/' + 
                         str(self.filesize))
        if end and end < self.filesize and end > start:
            self.fileobj.seek(start)  
            self.streamsize = end - start
            rangetext = (str(start) + '-' + str(end) + '/' + 
                         str(self.filesize)) 
        self.rangetext = rangetext

    # Be careful: if you call this your object is consumed and you will
    # need to create new one.
    def __str__(self):
        return self.fileobj.read()

    def __iter__(self):
        data = self.fileobj.read(self.chunksize)
        while data:
            yield data
            data = self.fileobj.read(self.chunksize)

    def __len__(self):
        return self.streamsize

    def get_rangetext(self):
        return 'bytes ' + self.rangetext if self.rangetext else ''

def atol(s, base=10):
    """
       atol(s, base) -> long

       Like long() in Python but works like C's atol() by
       trying to convert a portion of the string instead of chucking
       ValueError.
    """
    return atox(s, long, base)

def atoi(s, base=10):
    """
       atoi(s, base) -> int

       Like int() in Python but works like C's atoi() by 
       trying to convert a portion of the string instead of chucking
       ValueError.
    """
    return atox(s, int, base)

def atox(s, func, base=10):
    res = 0
    while s:
        try:
            res = func(s, base)
        except ValueError:
            s = s[:-1]
        else:
            break
    return res

def find_daap_tag(searchtag, data):
    """find_daap_tag(searchtag, data) -> value

    Given a daap tag and a decoded response, find the value associated with
    that tag.  If there are multiple only first one is returned.

    NB: This function uses recursion and MAY fail if your decoded data nests
    many levels (though this should never be the case).
    """
    try:
        for tag, value in data:
            if searchtag == tag:
                return value
            if type(value) == list:
                value = find_daap_tag(searchtag, value)
                if value:
                    return value
    # Recursion error is RuntimeError, treat it as failure.
    except (RuntimeError, ValueError):
        return None

def decode_response(reply):
    """
       decode_response(reply) -> reply

       decode_response takes a binary buffer containing the reply, then
       converts to an a Python representation.

       Things in a DMAP_TYPE_LIST container will contain a list with other
       response codes.
    """
    # This must be wrapped around a try ... except block in case the other
    # end lies to us about the size of the individual items.
    decoded = []
    try:
        while reply:
            headerfmt = '!4sI'
            headersize = struct.calcsize(headerfmt)
            code, size = struct.unpack(headerfmt, reply[:headersize])
            reply = reply[headersize:]
            realname, realtype = dmap_consts[code]
            realfmt, realsize = fmts[realtype]
            # XXX check size == realsize
            if realtype == DMAP_TYPE_LIST:
                decoded.append((code,
                                decode_response(reply[:size])))
                # next guy
                reply = reply[size:]
                continue
            if realtype == DMAP_TYPE_STRING:
                # overwrite the size for string with the size specified
                # by the server.
                realfmt = str(size) + realfmt 
            else:
                if realsize != size:
                    raise ValueError
                realfmt = '!' + realfmt
            realfmtsize = struct.calcsize(realfmt)
            (value, ) = struct.unpack(realfmt, reply[:realfmtsize])
            decoded.append((code, value))
            reply = reply[realfmtsize:]
        return decoded
    except (KeyError, ValueError), e:
        return [(-1, [])]

def encode_response(reply):
    """
       encode_response(reply) -> StreamObj/ChunkedStreamObj

       encode_response: takes a list of types containing codes and their 
       values, then converts to an appropriate thing that can be used 
       to send over the wire.

       DMAP_TYPE_LIST should have a value of list containing other response
       codes.
    """
    blob = ''
    subblob = ''
    try:
        for code, value in reply:
            nam, typ = dmap_consts[code]
            fmt, size = fmts[typ]
            if typ == DMAP_TYPE_LIST:
                # list container - override the value and the size.  Set
                # value to '' to append nothingness but tack on the subblob at 
                # the end. 
                subblob = str(encode_response(value))
                size = len(subblob)
                value = ''
            if typ == DMAP_TYPE_STRING:
                fmt = str(len(value)) + fmt
                size = len(value)
            # code (4 bytes), length (4 bytes), data (variable), network byte
            # order
            fmt = '!4sI' + fmt
            # XXX slow - should bunch up
            blob += struct.pack(fmt, code, size, value)
            blob += subblob
        blob = StreamObj(blob)
    except ValueError:
        # This is probably a file.  Just pass up to the
        # caller and let the caller deal with it.
        [(filepath, start, end)] = reply
        blob = ChunkedStreamObj(filepath, start, end)
    return blob

def split_url_path(urlpath):
    """
       split_url_path(urlpath) -> path, dict

       Takes a GET request and then splits it into the file component parts
       as a list and a dictionary of parameters.
    """
    print 'urlpath is %s' % urlpath
    parts = urlpath.split('?')
    if len(parts) > 1 and parts[1]:
        path, query = parts
        qdict = dict()
        # I think urllib won't split these for us (?) ... oh well.
        for q in query.split('&'):
            name, sep, value = q.partition('=')
            qdict[name] = urllib.unquote(value)
        url_sep = '/'
        # [1:] because we want to split out the first empty string, URI in form
        # of /xxx/yyy, '/xxx/yyy'.split(/') -> '', 'xxx', 'yyy'
        return [urllib.unquote(x) for x in path.split(url_sep)][1:], qdict
    else:
        # len(parts) == 1:
        return parts, None    # path only
