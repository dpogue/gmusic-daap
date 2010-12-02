#!/usr/bin/env python
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
from libdaap import *

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

        # XXX hardcoded module for ready-to-eat server.
        if use_mdns:
            install_mdns('pydaap', **kwargs)
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
