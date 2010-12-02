# mdns.py
#
# Very simple implementation of publishing service on Mac using mDNSResponder.

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
