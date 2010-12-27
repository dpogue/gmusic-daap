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

import pybonjour
import select
import errno

# Use a Python class so we can stash our state inside it.
class BonjourCallbacks(object):
    def __init__(self, user_callback):
        self.user_callback = user_callback
        self.refs = []

    def add_ref(self, ref):
        self.refs.append(ref)

    def del_ref(self, ref):
        self.refs.remove(ref)

    def get_refs(self):
        return self.refs

    def close(self):
        for ref in self.refs:
            ref.close()

    def __call__(self, ref):
        pybonjour.DNSServiceProcessResult(ref)

    def register_callback(self, sdRef, flags, errorCode, name, regtype,
                               domain):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return
        self.user_callback(sdRef, flags, errorCode, name, regtype, domain)

    def browse_callback(self, sdRef, flags, interfaceIndex, errorCode,
                        serviceName, regtype, replyDomain):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return

        if (flags & pybonjour.kDNSServiceFlagsAdd):
            self.added = True
        else:
            self.added = False

        ref = pybonjour.DNSServiceResolve(0,
                                          interfaceIndex,
                                          serviceName,
                                          regtype,
                                          replyDomain,
                                          self.resolve_callback)
        self.add_ref(ref)

    def resolve_callback(self, sdRef, flags, interfaceIndex, errorCode,
                         fullname, hosttarget, port, txtRecord):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return

        self.user_callback(self.added, fullname, hosttarget, port)
        self.del_ref(sdRef)
        sdRef.close()

def bonjour_register_service(name, regtype, port, callback):
    callback_obj = BonjourCallbacks(callback)
    ref = pybonjour.DNSServiceRegister(name=name,
                                       regtype=regtype,
                                       port=port,
                                       callBack=callback_obj.register_callback)
    callback_obj.add_ref(ref)
    return callback_obj

def bonjour_browse_service(regtype, callback):
    callback_obj = BonjourCallbacks(callback)
    ref = pybonjour.DNSServiceBrowse(regtype=regtype,
                                     callBack=callback_obj.browse_callback)
    callback_obj.add_ref(ref)
    return callback_obj
