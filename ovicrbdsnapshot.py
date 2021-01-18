#!/usr/bin/python

#
# Copyright (c) 2020 Marco Napolitano
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import time
from datetime import datetime
import subprocess
import os
import sys

# Declarations
basepath = '/opt/ovicbackup'
scriptlogfile = basepath+'/log/ovicrbdsnapshot.log'
statusbasefilename = basepath+'/status/ovicrbdsnapshot-'
rbdexec = '/bin/rbd'
grepexec = '/bin/grep'
awkexec = '/usr/bin/awk'
sortexec = '/usr/bin/sort'
poolname = 'YourCephPool'
userid = 'ovicbackup'
minsnapshots = 2
snapshotretentiondays = 1

# Log set up:
scriptpid = os.getpid()
scriptlogformat = logging.Formatter('[%(asctime)s] PID: '+str(scriptpid)+' - %(levelname)s: %(message)s')
scriptloghandler = logging.FileHandler( scriptlogfile )
scriptloghandler.setFormatter( scriptlogformat )
scriptlog = logging.getLogger( 'script' )
scriptlog.addHandler( scriptloghandler )
scriptlog.setLevel( logging.DEBUG )

# Write start notice into log:
scriptlog.info ( "script started." )

# One argument needed:
if len(sys.argv) !=  2:
   errmessage = "missing argument or too many arguments, you need to pass the image (ceph volume) as argument on the command line. No more, no less."
   print "ERROR: "+errmessage
   scriptlog.error( errmessage )
   sys.exit(1)

# Set the name of the image to backup:
imname = str(sys.argv[1])
scriptlog.info( "rbd image name \""+imname+"\" was passed as argument." )

# Write status file
statusfile = statusbasefilename+imname+'.status'
statf = open(statusfile,"w")
statf.write('PID:'+str(scriptpid))
statf.close()

# Get current date
currentdate = datetime.now()

# Define the name of the image snapshot by parsing the current date 
snapshotname = currentdate.strftime("%Y%m%d_%H%M%S")

# Get /dev/null file descriptor to redirect error output
devnullfo = open('/dev/null', 'wb')
devnullfileno = devnullfo.fileno()

# Create snapshot
scriptlog.info( "launching creation of snapshot for image \""+imname+"\"" )
subprocess.call( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'create', imname+'@'+snapshotname ], stderr = devnullfileno )
subprocess.call( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'protect', imname+'@'+snapshotname ], stderr = devnullfileno )

# Delete obsolete snapshots
scriptlog.info( "creation of new snapshot was done. Starting obsolete snapshot removal." )
psa = subprocess.Popen( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'ls', imname ], stdout = subprocess.PIPE, stderr = devnullfileno  )
psb = subprocess.Popen( [grepexec, '-iv', 'snapid'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $2}' ], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psb = subprocess.Popen( [grepexec, '-E', '^[[:digit:]]{8}_[[:digit:]]{6}$'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [sortexec, '-u'], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
outp = psa.communicate()[0]
imagesnaps = outp.splitlines()
foundsnaps = len(imagesnaps)
maxremovals = foundsnaps - minsnapshots
removalnum = 0
if maxremovals < 0: maxremovals = 0
scriptlog.info( "image \""+imname+"\" has "+str(foundsnaps)+" snapshots. Minimum number is "+str(minsnapshots)+". A maximum of "+str(maxremovals)+" snapshots will be removed, each snapshot will be removed only if its age is greater than retention time, which is "+str(snapshotretentiondays)+" days." )
scriptlog.info( "rbd volume snapshots removed till now: "+str(removalnum) )
for x in range (0, foundsnaps):
    cursnap = imagesnaps[x]
    scriptlog.info( "searching obsolete rbd volume snapshots, iteration "+str(x+1)+" - found rbd volume snapshot \""+cursnap+"\". Analyzing:" )
    snapdate = datetime.strptime(cursnap, "%Y%m%d_%H%M%S")
    scriptlog.info( "snapshot name: \""+cursnap+"\", parsed date: "+snapdate.strftime("%Y-%m-%d %H:%M:%S") )
    snapage = currentdate - snapdate
    snapagedays = snapage.total_seconds() / 86400
    scriptlog.info( "snapshot age in days: "+str(snapagedays) )
    if (removalnum < maxremovals) and (snapagedays > snapshotretentiondays):
        scriptlog.info( "the rbd volume snapshot \""+cursnap+"\" will be removed because it is "+str(snapagedays)+" days old and the maximum age is "+str(snapshotretentiondays)+" days." )
        subprocess.call( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'unprotect', imname+'@'+cursnap ], stderr = devnullfileno )
        subprocess.call( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'rm', imname+'@'+cursnap ], stderr = devnullfileno )
        removalnum += 1
        scriptlog.info( "rbd volume snapshots removed till now: "+str(removalnum) )

# Close /dev/null file object
statf = open(statusfile,"w")
statf.write('OK')
statf.close()
devnullfo.close()
scriptlog.info( "script finished. Exiting." )
sys.exit(0)
