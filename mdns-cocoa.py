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

# mdns.py
#
# Very simple implementation of publishing service on Mac using mDNSResponder.
# 
# NOTE: THIS FILE IS CURRENTLY NOT MAINTAINED AND IS UNUSED.

from Foundation import NSNetService, NSNetServiceBrowser, NSObject

class NetServicePublicationDelegate(NSObject):

    def netServiceWillPublish_(self, netService):
        pass

    def netService_didNotPublish_(self, netService, errorDict):
        print 'errorDict', errorDict
        pass

    def netServiceDidStop_(self, netService):
        pass

class NetServiceBrowserDelegate(NSObject):

    def set_callbacks(self, add_cb, remove_cb):
        self.add_cb = add_cb
        self.remove_cb = remove_cb

    def netServiceBrowserWillSearch_(self, browser):
        pass

    def netServiceBrowserDidStopSearch_(self, browser):
        pass

    def netServiceBrowser_didNotSearch_(self, browser, errorDict):
        # XXX error callback?
        print 'did not find search'
        pass

    def netServiceBrowser_didFindSearch_moreComing_(self, browser,
                                                   aNetService, moreComing):
        self.add_cb(aNetService)

    def netServiceBrowser_didRemoveService_moreComing_(self, browser,
                                                      aNetService, moreComing):
        self.remove_cb(aNetService)

# bonjour_service_xxx will be useful in the NetServiceBrowserDelegate
# callbacks.
def bonjour_service_port(service):
    return service.port()

def bonjour_service_type(service):
    return service.type()

def bonjour_service_name(service):
    return service.name()

def bonjour_publish_service(typ, nam):
    """
       bonjour_publish_service(typ, nam) -> handle

       Publishes service with given type and name and returns a handle
       to it.

       e.g. bonjour_publish_service('_daap._tcp', '')
    """
    service = NSNetService.alloc().initWithDomain_type_name_('', typ, nam)
    if service:
        delegate = NetServicePublicationDelegate.alloc().init()
        service.setDelegate_(delegate)
        service.publish()
    return service

def bonjour_stop_service(service):
    service.stop()

def bonjour_search_servicebytype(typ, add_cb, remove_cb):
    browser = NSNetServiceBrowser.alloc().init()
    delegate = NetServiceBrowserDelegate.alloc().init()
    delegate.set_callbacks(add_cb, remove_cb)
    browser.setDelegate_(delegate)
    browser.searchForServicesOfType_inDomain_(typ, '')
