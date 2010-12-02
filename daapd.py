#!/usr/bin/env python
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

# daapd.py - Example server frontend.
#
# Original Author: Geoffrey Lee
#
# !!! No user servicable parts below. !!!

import os
import sys
import getopt

# Hardcoded example backend
import filebackend
from pydaap.libdaap import *

VERSION = '0.1'

def version(prognam):
    print '%s version %s' % (prognam, VERSION)
    sys.exit(1)

def usage(prognam):
    print 'usage: %s [-vh] [[-c maxconn] [-p port] path]' % prognam
    sys.exit(1)

def main(argc, argv):
    # Set some defaults.
    prognam = argv[0]
    use_mdns = True
    kwargs = dict()
    try:
        try:
            opts, args = getopt.getopt(argv[1:], 'p:c:vhM')
        except getopt.GetoptError, e:
            print str(e)
            usage(prognam)
            # NOTREACHED
        for o, a in opts:
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

        if use_mdns:
            install_mdns('pydaap', **kwargs)
        # XXX hardcoded module for ready-to-eat server.
        backend = filebackend.Backend(args[0])
        server = make_daap_server(backend, **kwargs)
        runloop(server)

    # catch all
    except Exception, e:
        print 'An error occurred: ' + str(e)
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))
