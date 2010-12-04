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

import libdaap

VERSION = '0.1'

def usage(prognam):
    print 'usage: %s [-Svh] [addr:port]' % prognam
    sys.exit(1)

def version(prognam):
    print '%s %s' % (prognam, VERSION)
    sys.exit(1)

def scanmdns():
    try:
        # no callback: it will print debug data
        libdaap.browse_mdns(None)
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(1)

def find_db(response):
    print 'find_db:'
    print 'response: ', response
    return 1

def find_base_playlist(response):
    pass

def dump(host, kwargs):
    client = libdaap.make_daap_client(host, **kwargs)
    if not client.connect():
        print "Error: can't connect"
        return
    print 'session = ', client.session
    print 'db = ', client.db_id
    print 'dbname = ', client.db_name
    for k in client.playlists.keys():
        print 'playlist name = %s' % client.playlists[k]['name']
        print 'playlist count = %s' % client.playlists[k]['count']
        print 'base playlist = %s' % client.playlists[k]['base']
        for k_ in client.items[k].keys():
            print '    media kind = %s' % client.items[k][k_]['kind']
            print '    media name = %s' % client.items[k][k_]['name']
            print '    media duration = %s' % client.items[k][k_]['duration']
            print '    media size = %s' % client.items[k][k_]['size']
            print '    media enclosure = %s' % client.items[k][k_]['enclosure']
            print '    media path = %s' % client.daap_get_file_request(k_)

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

        if len(args) != 1:
            usage(prognam)

        host, sep, port = args[0].partition(':')
        
        if port:
            kwargs['port'] = int(port)

        dump(host, kwargs)

    except Exception, e:
        print 'An error occurred: ' + str(e)
        raise
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))
