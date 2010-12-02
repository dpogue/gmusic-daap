# libdaap.py
# Server implementation of DAAP

import os
# XXX merged into urllib.urlparse in Python 3
import urlparse
# XXX merged into http.server in Python 3.
import BaseHTTPServer
import SocketServer
import threading

import mdns
from const import *
from subr import (encode_response, split_url_path, atoi, atol, StreamObj,
                  ChunkedStreamObj)

# Configurable options (or do via command line).
DEFAULT_PORT = 3689
DAAP_TIMEOUT = 1800    # timeout (in seconds)

DAAP_MAXCONN = 10      # Number of maximum connections we want to allow.

# !!! No user servicable parts below. !!!

VERSION = '0.1'

DAAP_VERSION_MAJOR = 3
DAAP_VERSION_MINOR = 0
DAAP_VERSION = ((DAAP_VERSION_MAJOR << 16)|DAAP_VERSION_MINOR)

DMAP_VERSION_MAJOR = 2
DMAP_VERSION_MINOR = 0
DMAP_VERSION = ((DMAP_VERSION_MAJOR << 16)|DMAP_VERSION_MINOR)

DAAP_OK = 200          # Also sent with mstt
DAAP_NOCONTENT = 204   # Acknowledged but no content to send back
DAAP_FORBIDDEN = 403   # Access denied
DAAP_BADREQUEST = 400  # Bad URI request
DAAP_UNAVAILABLE = 503 # We are full

DEFAULT_CONTENT_TYPE = 'application/x-dmap-tagged'

class DaapTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True    # setsockopt(... SO_REUSEADDR, 1)

    # New functions in subclass.  Note: we can separate some of these out
    # into separate libraries but not now.
    def set_backend(self, backend):
        self.backend = backend

    def set_name(self, name):
        self.name = name

    def set_maxconn(self, maxconn):
        # NB: the DAAP session id can't be 0.
        # These are easily guessible ... maybe we should randomize.
        self.connpool = range(1, maxconn + 1)
        self.activeconn = dict()

    def daap_timeout_callback(self, s):
        self.del_session(s)

    def session_count(self):
        return len(self.activeconn)

    def new_session(self):
        if not self.connpool:
            return None
        s = self.connpool.pop()
        self.activeconn[s] = threading.Timer(DAAP_TIMEOUT,
                                             self.daap_timeout_callback,
                                             s)
        self.activeconn[s].start()
        return s

    def renew_session(self, s):
        try:
            self.activeconn[s].cancel()
        except KeyError:
            return False
        # Pants...  we need to create a new timer object.
        self.activeconn[s] = threading.Timer(DAAP_TIMEOUT,
                                             self.daap_timeout_callback,
                                             s)
        self.activeconn[s].start()
        # OK, thank the caller for telling us the guy's alive
        return True

    def del_session(self, s):
        # maybe the guy tried to trick us by running /logout with no active
        # conn.
        try:
            self.activeconn[s].cancel()
            # XXX can't just delete? - need to keep a reference count for the
            # connection, we can have data/control connection?
            del self.activeconn[s]
            self.connpool.append(s)
        except ValueError:
            pass

class DaapHttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'daap.py' + ' ' + VERSION

    # Not used at the moment.
    # def __init__(self, request, client_address, server):
    #    super(BaseHTTPRequestHandler, self).__init__(self, request,
    #                                                   client_address,
    #                                                   server)

    def finish(self):
        try:
            self.server.del_session(self.session)
        except AttributeError:
            pass
        # XXX Lousy python module.
        # super(DaapHttpRequestHandler, self).finish()
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.finish(self)
        except IOError:
            # Silence broken pipe error.
            pass

    def do_send_reply(self, rcode, reply, content_type=DEFAULT_CONTENT_TYPE,
                      extra_headers=[]):
        blob = encode_response(reply)
        try:
            self.send_response(rcode)
            self.send_header('Content-type', content_type)
            self.send_header('Daap-Server', self.server_version)
            self.send_header('Content-length', str(len(blob)))
            if blob.get_rangetext():
                print 'sending range %s' % blob.get_rangetext()
                self.send_header('Content-Range', blob.get_rangetext())
            # Note: we currently do not have the ability to replace or 
            # override the default headers.
            for k, v in extra_headers:
                self.send_header(k, v)
            self.end_headers()
            for chunk in blob:
                self.wfile.write(chunk)
        # Remote guy could be mean and cut us off.  If so, silence the broken
        # pipe error, and continue on our merry way
        except IOError:
            session = getattr(self, 'session', 0)
            if session:
                self.server.del_session(session)

    # Convenience function: convenient that session-id must be non-zero so
    # you can use it for True/False testing too.
    def get_session(self):
        path, query = split_url_path(self.path)
        session = 0
        if not query or not 'session-id' in query.keys():
            pass
        else:
            try:
                session = int(query['session-id'])
                if not self.server.renew_session(session):
                    session = 0
            except ValueError:
                pass
        return session

    def do_server_info(self):
        reply = []
        # Append standard codes
        reply.append(('mstt', DAAP_OK))   # OK
        reply.append(('apro', DAAP_VERSION))
        reply.append(('mpro', DMAP_VERSION))
        reply.append(('minm', self.server_version))    # XXX FIXME
        reply.append(('mstm', DAAP_TIMEOUT))

        # 'msup' not supported, but we don't indicate that by writing a 0.
        # We do it by leaving it out.
        not_supported = [
                         'msix',    # Indexing
                         'msex',    # Extensions
                         'msau',    # password?
                         'msqy',    # queries
                         'msrs',    # resolve
                         'msbr',    # browsing
                         'mspi',    # persistent ids
                        ]
        supported = [
                     'msal',        # auto-logout
                     'mslr'         # login
                    ]
        for code in not_supported:
            reply.append((code, 0))
        for code in supported:
            reply.append((code, 1))

        reply.append(('msdc', 1))   # database count

        # Wrap this around a msrv (server info) response
        reply = [('msrv', reply)]
        # Bye bye, butterfly ...
        return (DAAP_OK, reply, [])

    def do_content_codes(self):
        reply = []
        # build the content codes
        content_codes = []
        for k in dmap_consts.keys():
            desc, typ = dmap_consts[k]
            entry = []
            entry.append(('mcnm', k))
            entry.append(('mcna', desc))
            entry.append(('mcty', typ))
            content_codes.append(('mdcl', entry))
        reply = [('mccr', [('mstt', DAAP_OK)] + content_codes)]
        return (DAAP_OK, reply, [])

    # Note: we don't support authentication at the moment, when we do
    # send a 401 if there's no password and the client will re-issue the
    # /login.
    def do_login(self):
        # XXX If we are full, what does the server return?
        session = self.server.new_session()
        if not session:
            return (DAAP_UNAVAILABLE, [], [])
        # Stash a copy in case clients pull the rug under us so we can
        # still clean up in that case.  See the finish() routine.
        self.session = session
        reply = []
        reply.append(('mlog', [('mstt', DAAP_OK), ('mlid', session)]))
        # XXX Should we reject the login if there is no user-agent?  Rhythmbox
        # doesn't send one for some reason.
        return (DAAP_OK, reply, [])

    def do_logout(self):
        session = self.get_session()
        if not session:
           return (DAAP_FORBIDDEN, [], [])
        self.server.del_session(session)
        return (DAAP_NOCONTENT, [], [])

    # We don't support this but Rhythmbox sends this anyway.  Grr.
    def do_update(self):
        path, query = split_url_path(self.path)
        session = self.get_session()
        if not session:
            return (DAAP_FORBIDDEN, [], [])
        # UGH.  We should be updating this ... this is not supported at the 
        # moment.
        xxx_revision = 2
        reply = []
        reply.append(('mupd', [('mstt', DAAP_OK), ('musr', xxx_revision)]))
        return (DAAP_OK, reply, [])

    def do_stream_file(self, db_id, item_id):
        extra_headers = []
        # NOTE: Grabbing first header only.
        # XXX debug crap
        print 'do_stream_file'
        for k in self.headers.keys():
            print 'Header %s value %s' % (k, repr(self.headers.getheader(k)))
        # XXX backend API is broken FIXME  API should return a handle to the
        # open file.
        stream_file = self.server.backend.get_filepath(item_id)
        print 'streaming %s' % stream_file
        seekpos = seekend = 0
        rangehdr = self.headers.getheader('Range')
        if rangehdr:
            paramstring = 'bytes='
            if rangehdr.startswith(paramstring):
                seekpos = atol(rangehdr[len(paramstring):])
            idx = rangehdr.find('-')
            if idx >= 0:
                seekend = atol(rangehdr[(idx + 1):])
            if seekend < seekpos:
                seekend = 0
        # Return a special response, the encode_reponse() will handle correctly
        return (DAAP_OK, [(stream_file, seekpos, seekend)], extra_headers)

    def do_databases(self):
        path, query = split_url_path(self.path)
        session = self.get_session()
        if not session:
            return (DAAP_FORBIDDEN, [], [])
        if len(path) == 1:
            reply = []
            db = []
            count = len(self.server.backend.get_items())
            name = self.server.name
            db.append(('mlit', [
                                ('miid', 1),    # Item ID
                                ('mper', 1),    # Persistent ID
                                ('minm', name), # Name
                                ('mimc', count),# Total count
                                # Playlist is always non-zero because of
                                # default playlist.
                                ('mctc', 1)     # XXX Playlist count
                               ]))
            reply.append(('avdb', [
                                   ('mstt', DAAP_OK),   # OK
                                   ('muty', 0),         # Update type
                                   ('mtco', 1),         # Specified total count
                                   ('mrco', 1),         # Returned count
                                   ('mlcl', db)         # db listing
                                  ]))
            return (DAAP_OK, reply, [])
        else:
            # XXX might want to consider using regexp to do some complex
            # matching here.
            if path[2] == 'containers':
                return self.do_database_containers(path, query)
            elif path[2] == 'browse':
                return self.do_database_browse(path, query)
            elif path[2] == 'items':
                return self.do_database_items(path, query)
            elif path[2] == 'groups':
                return self.do_database_groups(path, query)
            else:
                return (DAAP_FORBIDDEN, [], [])

    def _check_db_id(self, db_id):
        return db_id == 1

    # do_database_xxx(self, path, query): helper functions.  Session already
    # checked and we know we are in database/xxx.
    def do_database_containers(self, path, query):
        db_id = int(path[1])
        if not self._check_db_id(db_id):
            return (DAAP_FORBIDDEN, [], [])
        reply = []
        if len(path) == 3:
            # We don't really support this at the moment, save for 
            # the requirement to send a default playlist.
            count = len(self.server.backend.get_items())
            default_playlist = [('mlit', [
                                          ('miid', 1),     # Item id
                                          ('minm', 'Library'),
                                          ('mper', 1),     # Persistent id
                                          ('mimc', count), # count - XXX dodgy
                                          ('mpco', 0),     # container ID
                                          ('abpl', 1)      # Base playlist 
                                         ]
                               )]
            reply.append(('aply', [                   # Database playlists
                                   ('mstt', DAAP_OK), # Status - OK
                                   ('muty', 0),       # Update type
                                   ('mtco', 1),       # total count - XXX fake!
                                   ('mrco', 1),       # returned count - XXX?
                                   ('mlcl', default_playlist)
                                  ]
                        ))
        else:
            # len(path) > 3
            playlistid = int(path[3])
            return self.do_itemlist(path, query, playlistid)
        return (DAAP_OK, reply, [])

    def do_database_browse(self, path, query):
        db_id = int(path[1])
        if not self._check_db_id(db_id):
            return (DAAP_FORBIDDEN, [], [])
        # XXX Browsing is not supported at the moment.
        return (DAAP_FORBIDDEN, [], [])

    # XXX TODO: a lot of junk we want to do here:
    # sort-headers - seems to be like asking the server to sort something
    # metadata - no support for this at the moment either.  Pretend we don't
    #            have any!!
    # type=xxx - not parsed yet.
    # transcoding - nupe, no support yet.
    # try to invoke any of this the server will go BOH BOH!!!! no support!!!
    def do_itemlist(self, path, query, playlist):
        items = self.server.backend.get_items()
        nfiles = len(items)
        itemlist = []

        # NB: mikd must be the first guy in the listing, then things can come
        # in any order.
        # XXX no metadata to send back at the moment.
        for k in items.keys():
            item = items[k]
            itemlist.append(('mlit', [       # Listing item
                                      # item kind - seems OK to hardcode this.
                                      ('mikd', DAAP_ITEMKIND_AUDIO),
                                      # item id - XXX fixme
                                      ('miid', k)
                                     ] + item
                           )) 
 
        tag = 'apso' if playlist else 'adbs'
        reply = []
        reply = [(tag, [                     # Container type
                        ('mstt', DAAP_OK),   # Status: OK
                        ('muty', 0),         # Update type
                        ('mtco', nfiles),    # Specified total count
                        ('mrco', nfiles),    # Returned count
                        ('mlcl', itemlist)   # Itemlist container
                       ]
                )]
        return (DAAP_OK, reply, [])

    def do_database_items(self, path, query):
        db_id = int(path[1])
        if not self._check_db_id(db_id):
            return (DAAP_FORBIDDEN, [], [])
        if len(path) == 3:
            # ^/database/id/items$
            return self.do_itemlist(path, query, None)
        if len(path) == 4:
            # Use atoi() here if only because Rhythmbox always pass us
            # junk at the end.
            item_id = atoi(path[3])
            print 'now playing item %d' % item_id
            return self.do_stream_file(db_id, item_id)
        
    def do_database_groups(self, path, query):
        db_id = int(path[1])
        if not self._check_db_id(db_id):
            return (DAAP_FORBIDDEN, [], [])

    def do_activity(self):
        # Getting the session automatically renews it for us.
        session = self.get_session()
        if not session:
            return (DAAP_FORBIDDEN, [], [])
        return (DAAP_NOCONTENT, [], [])

    def do_GET(self):
        # Farm off to the right request URI handler.
        # XXX jump table?
        # TODO XXX - add try: except block to protect against nasty
        # Handle iTunes 10 sending absolute path, and work around a limitation
        # in urlparse (doesn't support daap but it's basically the same
        # as http).
        endconn = False
        try:
            # You can do virtual host with this but we don't support for now
            # and actually strip it out.
            if self.path.startswith('daap://'):
                tmp = 'http://' + self.path[len('daap://'):]
                result = urlparse.urlparse(tmp)
                # XXX shouldn't overwrite this but we'll fix it later
                if result.query:
                    self.path = '?'.join([result.path, result.query])
                else:
                    self.path = result.path
            if self.path == '/server-info':
                rcode, reply, extra_headers = self.do_server_info()
            elif self.path == '/content-codes':
                rcode, reply, extra_headers = self.do_content_codes()
            elif self.path == '/login':
                rcode, reply, extra_headers = self.do_login()
            elif self.path == '/logout':
               rcode, reply, extra_headers = self.do_logout()
               endconn = True
            # /activity?session-id=xxxxx
            # XXX we should be splitting these so the path and the querystring
            # are separate.
            elif self.path.startswith('/activity'):
                rcode, reply, extra_headers = self.do_activity()
            elif self.path.startswith('/update'):
                rcode, reply, extra_headers = self.do_update()
            elif self.path.startswith('/databases'):
                rcode, reply, extra_headers = self.do_databases()
            else:
                # Boh-boh.  Unrecognized URI.  Send HTTP/1.1 bad request 400.
                rcode = DAAP_BADREQUEST
                reply = []
                extra_headers = []
        except Exception, e:
            print 'Error: Exception occurred: ' + str(e)
            # XXX should we end the connection on an exception occurence?
            rcode = DAAP_BADREQUEST
            reply = []
            extra_headers = []
        print 'do_GET: send reply with HTTP code %d' % rcode
        self.do_send_reply(rcode, reply, extra_headers=extra_headers)
        if endconn:
            self.wfile.close()

# Example callback: there isn't much to do here right now.
def mdns_callback(sdRef, flags, errorCode, name, regtype, domain):
    # XXX error handling?
    if errorCode != mdns.pybonjour.kDNSServiceErr_NoError:
        pass
    else:
        pass

def install_mdns(name, service='_daap._tcp', port=DEFAULT_PORT,
                 mdns_callback=mdns_callback):
    # XXX: what to do if this doesn't work?
    return mdns.bonjour_register_service(name, '_daap._tcp', port=DEFAULT_PORT,
        callback=mdns_callback)

def uninstall_mdns(ref):
    mdns.bonjour_unregister_service(ref)

def runloop(daapserver):
    daapserver.serve_forever()

def make_daap_server(backend, name='pydaap', port=DEFAULT_PORT,
                     max_conn=DAAP_MAXCONN):
    handler = DaapHttpRequestHandler
    httpd = DaapTCPServer(('', port), handler)
    httpd.set_name(name)
    httpd.set_backend(backend)
    httpd.set_maxconn(max_conn)
    return httpd

###############################################################################
