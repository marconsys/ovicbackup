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
from datetime import timedelta
import subprocess
import re
import os
import sys

# Declarations:
basepath = '/opt/ovicbackup'
scriptlogfile = basepath+'/log/ovicrbdbackup.log'
statusbasefilename = basepath+'/status/ovicrbdbackup-'
tmppath = basepath+'/tmp'
backy2exec = '/home/ovicbackup/.local/bin/backy2'
rbdexec = '/bin/rbd'
grepexec = '/bin/grep'
awkexec = '/usr/bin/awk'
sortexec = '/usr/bin/sort'
headexec = '/usr/bin/head'
tailexec = '/usr/bin/tail'
poolname = 'YourCephPool'
userid = 'ovicbackup'

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

# Set tmp diff file path:
difftmpfile = tmppath+'/'+imname+'.diff'

# Write status file:
statusfile = statusbasefilename+imname+'.status'
statf = open(statusfile,"w")
statf.write('PID:'+str(scriptpid))
statf.close()

# Get current date:
currentdate = datetime.now()
curdatestr = currentdate.strftime("%Y%m%d_%H%M%S")
curdatestrday = currentdate.strftime("%Y%m%d")

# Set expiration date:
expdate = currentdate + timedelta(days=100)
expdatestr = expdate.strftime("%Y-%m-%dT%H:%M:%S")

# Get /dev/null file descriptor to redirect error output:
devnullfo = open('/dev/null', 'wb')
devnullfileno = devnullfo.fileno()

# Check out last snapshot for the rbd image:
newsnaptodo = False
lastsnap = None
psa = subprocess.Popen( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'ls', imname ], stdout = subprocess.PIPE, stderr = devnullfileno  )
psb = subprocess.Popen( [grepexec, '-iv', 'snapid'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $2}' ], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psb = subprocess.Popen( [grepexec, '-E', '^[[:digit:]]{8}_[[:digit:]]{6}$'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [sortexec, '-u'], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
outp = psa.communicate()[0]
outplines = outp.splitlines()
if len(outplines) >= 1:
   psb = subprocess.Popen( [tailexec, '-n1'], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
   psb.stdin.write( outp )
   lastsnap = psb.communicate()[0].splitlines()[0]
   lastdate = datetime.strptime(lastsnap, "%Y%m%d_%H%M%S")
   elapsedtime = currentdate-lastdate
   elapsedtimesecs = elapsedtime.total_seconds()
   if elapsedtimesecs < 72000:   # if last snapshot younger than 20 hours
      scriptlog.info( "last snapshot for rbd image \""+imname+"\" was found, is called \""+lastsnap+"\"" )
   else:
      newsnaptodo = True
else:
   newsnaptodo = True
if newsnaptodo:
   scriptlog.info( "last snapshot not present or too old, launching creation of snapshot for image \""+imname+"\"" )
   lastsnap = currentdate.strftime("%Y%m%d_%H%M%S")
   outp = subprocess.check_output( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'create', imname+'@'+lastsnap], stderr = devnullfileno )
   for line in outp.splitlines():
      scriptlog.info( line )
   outp = subprocess.check_output( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'protect', imname+'@'+lastsnap], stderr = devnullfileno )
   for line in outp.splitlines():
      scriptlog.info( line )
   scriptlog.info( "last snapshot for rbd image \""+imname+"\" was just made, is called \""+lastsnap+"\"" )

# Check out second-last snapshot for the rbd image:
secosnap = None
psa = subprocess.Popen( [rbdexec, '-p', poolname, '--id', userid, 'snap', 'ls', imname ], stdout = subprocess.PIPE, stderr = devnullfileno  )
psb = subprocess.Popen( [grepexec, '-iv', 'snapid'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $2}' ], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psb = subprocess.Popen( [grepexec, '-E', '^[[:digit:]]{8}_[[:digit:]]{6}$'], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [sortexec, '-u'], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
outp = psa.communicate()[0]
outplines = outp.splitlines()
if len(outplines) >= 2:
   psb = subprocess.Popen( [tailexec, '-n2'], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
   psb.stdin.write( outp )
   tailout = psb.communicate()[0]
   psa = subprocess.Popen( [headexec, '-n1'], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
   psa.stdin.write( tailout )
   secosnap = psa.communicate()[0].splitlines()[0]
   secodate = datetime.strptime(secosnap, "%Y%m%d_%H%M%S")
   scriptlog.info( "second-last snapshot for rbd image \""+imname+"\" was found, is called \""+secosnap+"\"" )

# Backup:
lastback = None
secoback = None
newbacktodo = True
newbackfull = False
psa = subprocess.Popen( [backy2exec, 'ls', '-f', 'name,snapshot_name,valid,uid', '-s', lastsnap, imname], stdout = subprocess.PIPE, stderr = devnullfileno  )
psb = subprocess.Popen( [grepexec, ' 1 '], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
psa = subprocess.Popen( [sortexec], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
outplines = psa.communicate()[0].splitlines()
if len(outplines) >= 1:
   newbacktodo = False
   psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $8}' ], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
   psa.stdin.write( outplines[0] )
   lastback = psa.communicate()[0].splitlines()[0]
   scriptlog.info( "backup for last snapshot \""+lastsnap+"\" of rbd image \""+imname+"\" is already present, uid: \""+lastback+"\". Nothing to do." )
else:
   psa = subprocess.Popen( [backy2exec, 'ls', '-f', 'name,snapshot_name,valid,uid', '-t', 'from_zero', imname], stdout = subprocess.PIPE, stderr = devnullfileno  )
   psb = subprocess.Popen( [grepexec, ' 1 '], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
   psa = subprocess.Popen( [sortexec, '-r'], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
   outplines = psa.communicate()[0].splitlines()
   if len(outplines) >= 1:
      psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $4}' ], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
      psa.stdin.write( outplines[0] )
      snapname = psa.communicate()[0].splitlines()[0]
      snapdate = datetime.strptime(snapname, "%Y%m%d_%H%M%S")
      elapsedtime = currentdate-snapdate
      elapsedtimesecs = elapsedtime.total_seconds()
      if elapsedtimesecs > 2592000: # if last backup from scratch older than 30 days
         newbackfull = True
         scriptlog.info( "of backups present for rbd image \""+imname+"\", the last done from scratch is more than 30 days old. So backup of \""+lastsnap+"\" will be from scratch." ) 
      else:
         if secosnap is None:
            newbackfull = True
            scriptlog.info( "for rbd image \""+imname+"\", there is no second-last snapshot available. So backup of \""+lastsnap+"\" will be from scratch." )
         else:
            psa = subprocess.Popen( [backy2exec, 'ls', '-f', 'name,snapshot_name,valid,uid', '-s', secosnap, imname], stdout = subprocess.PIPE, stderr = devnullfileno  )
            psb = subprocess.Popen( [grepexec, ' 1 '], stdin = psa.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
            psa = subprocess.Popen( [sortexec], stdin = psb.stdout , stdout = subprocess.PIPE, stderr = devnullfileno )
            outplines = psa.communicate()[0].splitlines()
            if len(outplines) >= 1:
               psa = subprocess.Popen( [awkexec, '-F', ' ', '{print $8}' ], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = devnullfileno )
               psa.stdin.write( outplines[0] )
               secoback = psa.communicate()[0].splitlines()[0]
               scriptlog.info( "backup for second-last snapshot \""+secosnap+"\" of rbd image \""+imname+"\" is present, uid: \""+secoback+"\". So backup of \""+lastsnap+"\" will be differential." )
            else:
               newbackfull = True
               scriptlog.info( "for rbd image \""+imname+"\", second-last snapshot is \""+secosnap+"\", but has no backup. So backup of \""+lastsnap+"\" will be from scratch." )
   else:
      newbackfull = True
      scriptlog.info( "of backups present for rbd image \""+imname+"\", none is from scratch. So backup of \""+lastsnap+"\" will be from scratch." )


if newbacktodo:
   if newbackfull:
      scriptlog.info( "starting creation of rbd diff temporary file \""+difftmpfile+"\" for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\"." )
      difftmpfo = open(difftmpfile, 'wb')
      difftmpfileno = difftmpfo.fileno()
      subprocess.call( [rbdexec, 'diff', '--id', userid, '--whole-object', poolname+'/'+imname+'@'+lastsnap, '--format=json'], stdout = difftmpfileno, stderr = devnullfileno )
      scriptlog.info( "rbd diff temporary file \""+difftmpfile+"\" for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", was just created from scratch." )
      difftmpfo.close()
      scriptlog.info( "starting backup from scratch for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", using rbd diff temporary file \""+difftmpfile+"\"." )
      subprocess.call( [backy2exec, 'backup', '-s', lastsnap, '-r', difftmpfile, '-t', 'from_zero', '-e', expdatestr, 'rbd://'+poolname+'/'+imname+'@'+lastsnap, imname], stdout = devnullfileno, stderr = devnullfileno )
      scriptlog.info( "backup for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", was just done with backy2, using rbd diff temporary file \""+difftmpfile+"\"." )
      os.remove(difftmpfile)
      scriptlog.info( "rbd diff temporary file \""+difftmpfile+"\" was removed." )
   else:
      scriptlog.info( "starting creation of rbd diff temporary file \""+difftmpfile+"\" for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\"." )
      difftmpfo = open(difftmpfile, 'wb')
      difftmpfileno = difftmpfo.fileno()
      subprocess.call( [rbdexec, 'diff', '--id', userid, '--whole-object', poolname+'/'+imname+'@'+lastsnap, '--from-snap', secosnap, '--format=json'], stdout = difftmpfileno, stderr = devnullfileno )
      scriptlog.info( "rbd diff temporary file \""+difftmpfile+"\" for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", was just created as difference from snapshot \""+secosnap+"\"." )
      difftmpfo.close()
      scriptlog.info( "starting differential backup for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", using rbd diff temporary file \""+difftmpfile+"\", and backup \""+secoback+"\" of snapshot \""+secosnap+"\" as base version." )
      subprocess.call( [backy2exec, 'backup', '-s', lastsnap, '-r', difftmpfile, '-f', secoback, '-e', expdatestr, 'rbd://'+poolname+'/'+imname+'@'+lastsnap, imname], stdout = devnullfileno, stderr = devnullfileno )
      scriptlog.info( "backup for snapshot \""+lastsnap+"\" of rbd image \""+imname+"\", was just done with backy2, using rbd diff temporary file \""+difftmpfile+"\"." )
      os.remove(difftmpfile)
      scriptlog.info( "rbd diff temporary file \""+difftmpfile+"\" was removed." )

# Delete obsolete backups:
scriptlog.info( "starting deletion of expired backup images." )
psa = subprocess.Popen( [backy2exec, '-ms', 'ls', '-e', '-f', 'uid'], stdout = subprocess.PIPE, stderr = devnullfileno )
outplines = psa.communicate()[0].splitlines()
for line in outplines:
   print ( backy2exec+" rm "+line )
   subprocess.call( [backy2exec, 'rm', line], stdout = devnullfileno, stderr = devnullfileno )
print ( backy2exec+" cleanup" )
subprocess.call( [backy2exec, 'cleanup'], stdout = devnullfileno, stderr = devnullfileno )
scriptlog.info( "deletion of expired backup images completed." )

# Write status and exit:
statf = open(statusfile,"w")
statf.write('OK')
statf.close()
devnullfo.close()
scriptlog.info( "script finished. Exiting." )
sys.exit(0)

