#!/usr/bin/env python
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

# daap.py - Example client frontend
#
# Original Author: Geoffrey Lee

# !!! No user-serviceable parts below !!! 

import os
import sys
import getopt
# XXX http.client in Python 3
import httplib

from pydaap.libdaap import *
from subr import decode_response
import mdns

VERSION = '0.1'

MDNS_SERVICENAME = '_daap._tcp'

def usage(prognam):
    print 'usage: %s [-Svh] [addr:port]' % prognam
    sys.exit(1)

def version(prognam):
    print '%s %s' % (prognam, VERSION)
    sys.exit(1)

def scanmdns():
    print 'error: not supported, use mDNS(1) or avahi-browse(1)'
    sys.exit(1)

def handleresponse(response):
    print 'HTTP status %d %s' % (response.status, response.reason)
    if response.status == httplib.OK:
        return response.read()
    if response.status >= httplib.BAD_REQUEST:
        print 'Error: boh boh...'
        return None
    else:
        print 'Unsupported http response'
        return None

# XXX perform more checks, as is it is a bit dodgy
def find_session(response):
    print 'find_session:'
    print 'response: ', response
    try:
        [(code, body)] = response
        if code != 'mlog':
            raise ValueError
        [ok, session_msg] = body
        code, body = session_msg
        return body
    except ValueError:
        pass
    return 0

def find_db(response):
    print 'find_db:'
    print 'response: ', response
    return 1

def find_base_playlist(response):
    pass

def playinorder(host, save_dir, port=DEFAULT_PORT):
    conn = httplib.HTTPConnection(host, port)
    print 'playinorder: /server-info'
    conn.request('GET', '/server-info')
    # Don't really care about what I get back here.
    response = conn.getresponse()
    handleresponse(response)
    # Don't really care about this one either ...
    print 'playinorder: /content-codes'
    conn.request('GET', '/content-codes')
    response = conn.getresponse()
    handleresponse(response)
    # Login ...
    print 'playinorder: /login'
    conn.request('GET', '/login')
    response = decode_response(handleresponse(conn.getresponse()))
    session_id = find_session(response)
    if not session_id:
        print 'no session'
        # XXX error handling?
    print 'session-id = %d' % session_id
    print 'playinorder: /databases'
    conn.request('GET', '/databases?session-id=%d' % session_id)
    response = decode_response(handleresponse(conn.getresponse()))
    db_id = find_db(response)
    if not db_id:
        print 'no database id found'
        # XXX error handling?
    #(pl_id, playlist) = find_base_playlist(response)
    #if not pl_id:
    #    print 'no playlist id found'
    #    # XXX error handling?
    # XXX HACK
    playlist = []
    playlist.append((2, 'mp3'))
    for item in playlist:
        #(itemid, itemtype, itemname) = item
        (itemid, itemtype) = item
        print 'playinorder: downloading item %d type %s' % (itemid, itemtype)
        conn.request('GET', (('/databases/%d/items/%d.%s?meta=' +
                             'dmap.itemkind,dmap.itemid,' + 
                             'dmap.containeritemid&session-id=%d') %
                             (db_id, itemid, itemtype, session_id)))
        rawdata = handleresponse(conn.getresponse())
        filename = '.'.join([str(itemid), itemtype])
        open(os.path.join(save_dir, filename), 'wb').write(rawdata)
    conn.close()

def main(argc, argv):
    prognam = argv[0]
    kwargs = dict()
    try:
        try:
            opts, args = getopt.getopt(argv[1:], 'vhS')
        except getopt.GetoptError, e:
            print str(e)
            usage(prognam)
        for o, a in opts:
            if o == '-v':
                version(prognam)
                # NOTREACHED
            if o == '-h':
                usage(prognam)
                # NOTREACHED
            if o == '-S':
                scanmdns()
                # NOTREACHED

        if len(args) != 2:
            usage(prognam)

        host, sep, port = args[0].partition(':')
        save_dir = args[1]
        
        if port:
            kwargs['port'] = int(port)

        playinorder(host, save_dir, **kwargs)

    except Exception, e:
        print 'An error occurred: ' + str(e)
        raise
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))
