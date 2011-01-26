#!/usr/bin/env python
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

# daapd.py - Example server frontend.
#
# Original Author: Geoffrey Lee
#
# !!! No user servicable parts below. !!!

import errno
import os
import sys
import getopt
import select

# Hardcoded example backend
import filebackend
import libdaap

VERSION = '0.1'

def version(prognam):
    print '%s version %s' % (prognam, VERSION)
    sys.exit(1)

def usage(prognam):
    print 'usage: %s [-dMvh] [[-c maxconn] [-p port] path]' % prognam
    sys.exit(1)

def mdns_register_callback(name):
    pass

def main(argc, argv):
    # Set some defaults.
    prognam = argv[0]
    use_mdns = True
    debug = False
    kwargs = dict()
    try:
        try:
            opts, args = getopt.getopt(argv[1:], 'p:c:vhdM')
        except getopt.GetoptError, e:
            print str(e)
            usage(prognam)
            # NOTREACHED
        for o, a in opts:
            if o == '-d':
                debug = True
            if o == '-p':
                kwargs['port'] = int(a)
            if o == '-v':
                version(prognam)
                # NOTREACHED
            if o == '-c':
                kwargs['max_conn'] = int(a)
            if o == '-M':
                use_mdns = False
            if o == '-h':
                usage(prognam)
                # NOTREACHED
        if len(args) != 1:
            usage(prognam)

        # XXX hardcoded module for ready-to-eat server.
        backend = filebackend.Backend(args[0])
        if debug:
            print 'info: debug on'
        server = libdaap.make_daap_server(backend, debug=debug, **kwargs)
        if not server:
            raise RuntimeError('Cannot instiantiate server instance')
        # In robust mode, the server can return a port that's different
        # from the one we requested.
        address, port = server.server_address
        kwargs['port'] = port
        refs = []
        server_fileno = server.fileno()
        if use_mdns:
            if not libdaap.mdns_init():
                print 'warning: no mdns support found on system, disabled'
            else:
                callback = libdaap.mdns_register_service('pydaap',
                                                         mdns_register_callback,
                                                         **kwargs)
                refs = callback.get_refs()
        while True:
            try:
                rset = [server_fileno] + refs
                r, w, x = select.select(rset, [], [])
                for ref in refs:
                    if ref in r:
                        callback(ref)
                if server_fileno in r:
                    server.handle_request()
            except select.error, (err, errstring):
                if err == errno.EINTR:
                    continue
                else:
                    raise
    # catch all
    except Exception, e:
        print 'An error occurred: ' + str(e)
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))
