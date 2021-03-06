#!/usr/bin/python
#
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
#
#
#
#
# This input source is taken from the forked-daapd-0.12/src/httpd_daap.c.
# One correction was made to mcnm, change from UINT to STRING because that's
# what it is.
#
# DMAP_TYPE_XXX taken from forked-daapd-0.12./src/dmap_helpers.h.
# DAAP_MEDIAKIND_XXX and DAAP_SONGITEMKIND_XXX taken from 
# forked-daapd-0.12/src/db.c.
# Other individual values have documentation on where it came from.

import sys

src = 'const.txt'
dst = 'const.py'

# DMAP_TYPE_UBYTE   = 0x01
# DMAP_TYPE_BYTE    = 0x02
# DMAP_TYPE_USHORT  = 0x03
# DMAP_TYPE_SHORT   = 0x04
# DMAP_TYPE_UINT    = 0x05
# DMAP_TYPE_INT     = 0x06
# DMAP_TYPE_ULONG   = 0x07
# DMAP_TYPE_LONG    = 0x08
# DMAP_TYPE_STRING  = 0x09
# DMAP_TYPE_DATE    = 0x0a
# DMAP_TYPE_VERSION = 0x0b
# DMAP_TYPE_LIST    = 0x0c
typs = ['BYTE', 'SHORT', 'INT', 'LONG']
etyps = ['STRING', 'DATE', 'VERSION', 'LIST']

# daap.songitemkind - fill in others?
# DAAP_ITEMKIND = 0x2

# daap.songdatakind:
# DAAP_SONGDATAKIND_FILE   = 0x0
# DAAP_SONGDATAKIND_STREAM = 0x1

# daap.mediakind - XXX fixme: need to decode type 10, type 64.
# DAAP_MEDIAKIND_AUDIO = 1
# DAAP_MEDIAKIND_VIDEO = 2
# DAAP_MEDIAKIND_MOVIE = 32
# DAAP_MEDIAKIND_TV    = 64
 
lines = open(src, 'rb').readlines()
outfile = open(dst, 'wb')
outfile.write('# const.py\n')
outfile.write('# AUTOMATICALLY GENERATED - do not edit\n\n')

# write out the constants.

mediakinds = dict(AUDIO=1, VIDEO=2, MOVIE=32, TV=64)
songdatakinds = dict(FILE=0, STREAM=1)
itemkinds = dict(AUDIO = 2)
for k in itemkinds.keys():
    outfile.write('DAAP_ITEMKIND_%s = %d\n' % (k, itemkinds[k]))
outfile.write('\n')
for k in mediakinds.keys():
    outfile.write('DAAP_MEDIAKIND_%s = %d\n' % (k, mediakinds[k]))
outfile.write('\n')
for k in songdatakinds.keys():
    outfile.write('DAAP_SONGDATAKIND_%s = %d\n' % (k, songdatakinds[k]))
outfile.write('\n')

type_code = 0x1
for typ in typs:
    outfile.write('DMAP_TYPE_%s = 0x%x\n' % (typ, type_code))
    type_code += 1
    outfile.write('DMAP_TYPE_U%s = 0x%x\n' % (typ, type_code))
    type_code += 1
for etyp in etyps:
    outfile.write('DMAP_TYPE_%s = 0x%x\n' % (etyp, type_code))
    type_code += 1

outfile.write('\n')

outfile.write('dmap_consts = {\n')
for line in lines:
    # '[//]static const struct dmap_xxx dmap_yyy = 
    # { "yyy", "name", DMAP_TYPE_XXX };
    splitline = line.split()
    code = splitline[7].strip(',')
    name = splitline[8].strip(',')
    typ = splitline[9].strip(',')
    spacing = '    '
    if splitline[0].startswith('//'):
        spacing = '#   '
    outfile.write('%s%s: (%s, %s),\n' % (spacing, code, name, typ))
outfile.write('}\n')

outfile.write('\n')
outfile.write('dmap_consts_rmap = {\n')
for line in lines:
    splitline = line.split()
    code = splitline[7].strip(',')
    name = split = splitline[8].strip(',')
    spacing = '    '
    if splitline[0].startswith('//'):
        spacing = '#   '
    outfile.write('%s%s: %s,\n' % (spacing, name, code))
outfile.write('}\n')
        
outfile.close()
sys.exit(0)
