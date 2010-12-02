# mdns.py
#

import pybonjour

# Example callback
def register_callback(sdRef, flags, errorCode, name, regtype, domain):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        pass
    else:
        pass

def bonjour_unregister_service(ref):
    ref.close()

def bonjour_register_service(name, regtype, port, callback):
    ref = pybonjour.DNSServiceRegister(name=name,
                                       regtype=regtype,
                                       port=port,
                                       callBack=callback)
    # XXX We can set up a select() here but nevermind, we'll just wait.
    # This relies on the mDNSResponder/avahi running, which we might
    # not want to count on.
    pybonjour.DNSServiceProcessResult(ref)
    return ref

