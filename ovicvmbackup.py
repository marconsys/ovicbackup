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
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import re
import os
import sys

# Declarations:
engineurl = 'https://ovirtengine00.companyintranet.dom/ovirt-engine/api'
engineuser = 'ovicbackup@internal'
enginepass = 'YourPasswordHere'
basepath = '/opt/ovicbackup'
enginecafile = basepath+'/etc/ovicvmbackup.pem'
scriptlogfile = basepath+'/log/ovicvmbackup.log'
engineconnlogfile = basepath+'/log/ovicvmbackup-engineconn-debug.log'
statusbasefilename = basepath+'/status/ovicvmbackup-'
stordomname = 'YourExportStorageDomain'
snapshotnameprefix = 'ovicvmbackup'
backupvmprefix = 'ovicvmbackup'
clustername = 'YourOvirtCluster'
snapshottimeoutsecs = 3600
clonedvmtimeoutsecs = 7200
backexprtimeoutsecs = 3600
minbackupvms = 2
backupretentiondays = 13

# Log set up:
scriptpid = os.getpid()
engineconnlogformat = logging.Formatter('[%(asctime)s] PID: '+str(scriptpid)+' - %(levelname)s: %(message)s')
engineconnloghandler = logging.FileHandler( engineconnlogfile )
engineconnloghandler.setFormatter( engineconnlogformat )
engineconnlog = logging.getLogger( 'engineconn' )
engineconnlog.addHandler( engineconnloghandler )
engineconnlog.setLevel( logging.DEBUG )
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
   errmessage = "missing argument or too many arguments, you need to pass the vm name as argument on the command line. No more, no less. Exiting."
   print "ERROR: "+errmessage
   scriptlog.error( errmessage )
   sys.exit(1)

# Set the name of the VM to backup:
vmname = str(sys.argv[1])
scriptlog.info( "vm name \""+vmname+"\" was passed as argument." )

# Write status file:
statusfile = statusbasefilename+vmname+'.status'
statf = open(statusfile,"w")
statf.write('PID:'+str(scriptpid))
statf.close()

# Define prefix and suffix of snapshot name and of backup VM name:
backupdate = datetime.now().strftime("%Y%m%d_%H%M%S")
snname = snapshotnameprefix+"-"+backupdate

# Connection to oVirt/RHV engine:
scriptlog.info( "trying to connect to engine." )
engineconn = sdk.Connection(
    url = engineurl,
    ca_file = enginecafile,
    username = engineuser,
    password = enginepass,
    log = engineconnlog,
    debug = True
)

# Get sdk services:
sysserv = engineconn.system_service()
vmsserv = engineconn.system_service().vms_service()
stordomsserv = engineconn.system_service().storage_domains_service()
vms = vmsserv.list()
vm = next(
   (curvm for curvm in vms if curvm.name == vmname),
   None
)
if vm is None:
    errmessage = "vm \""+vmname+"\" was searched inside a list of "+str(len(vms))+" vms but it was not found. It seems it doesn't exist on this cluster. Exiting."
    scriptlog.error( errmessage )
    statf = open(statusfile,"w")
    statf.write("KO - "+errmessage)
    statf.close()
    engineconn.close()
    sys.exit(1)    
scriptlog.info( "found vm \""+vmname+"\", inside a list of "+str(len(vms))+" vms." )
vmserv = vmsserv.vm_service(vm.id)
snapsserv = vmsserv.vm_service(vm.id).snapshots_service()
stordoms = stordomsserv.list()
stordom = next(
   (curstordom for curstordom in stordoms if curstordom.name == stordomname),
   None
)
if stordom is None:
     errmessage = "storage domain \""+stordomname+"\" was searched inside a list of "+str(len(stordoms))+" storage domains but it was not found. It seems it doesn't exist on this cluster. Exiting."
     scriptlog.error( errmessage )
     statf = open(statusfile,"w")
     statf.write("KO - "+errmessage)
     statf.close()
     engineconn.close()
     sys.exit(1)
scriptlog.info( "found storage domain \""+stordomname+"\", inside a list of "+str(len(stordoms))+" storage domains." )
stordomserv = stordomsserv.storage_domain_service(stordom.id)

# Create snapshot for backup:
snapsserv.add(
  types.Snapshot(
    description = snname,
    persist_memorystate = False,
  ),
)
scriptlog.info( "requested temporary snapshot \""+snname+"\" for backup of vm \""+vmname+"\". Waiting for creation." )

# Wait for the backup snapshot to become ready:
timeoutstart = datetime.now()
while True:
    time.sleep(5)
    elapsedtime = datetime.now()-timeoutstart
    elapsedtimesecs = elapsedtime.total_seconds()
    snaps = snapsserv.list()
    backsnap = next(
       (cursnap for cursnap in snaps if cursnap.description == snname),
       None
    )
    if backsnap.snapshot_status == types.SnapshotStatus.OK:
        break
    elif elapsedtimesecs > snapshottimeoutsecs :
        errmessage = "the creation of the snapshot \""+snname+"\" for the vm \""+vmname+"\" has timed out after "+str(snapshottimeoutsecs)+" seconds. It's still possible snapshot creation finishes correctly on the cluster, later. Exiting."
        scriptlog.error( errmessage )
        statf = open(statusfile,"w")
        statf.write("KO - "+errmessage)
        statf.close()
        engineconn.close()
        sys.exit(1)
    else:
        scriptlog.info( "the status of snapshot \""+snname+"\" for vm \""+vmname+"\" is still \""+str(backsnap.snapshot_status)+"\", waiting until it's \"ok\". Elapsed time: "+str(int(elapsedtimesecs))+" seconds, timeout triggers after "+str(snapshottimeoutsecs)+" seconds." )
scriptlog.info( "the temporary snapshot \""+snname+"\" for backup of vm \""+vmname+"\" was created." )

# Create backup vm, cloning it from the snapshot:
snaps = snapsserv.list()
backsnap = next(
   (cursnap for cursnap in snaps if cursnap.description == snname),
   None
)
snapserv = snapsserv.snapshot_service(backsnap.id)
backupvmname = backupvmprefix+"-"+vmname+"-"+backupdate
backupvm = vmsserv.add(
    vm = types.Vm(
        name = backupvmname,
        snapshots = [
            types.Snapshot(
                id = backsnap.id
            )
        ],
        cluster = types.Cluster(
            name = clustername
        )
    )
)
scriptlog.info( "requested creation of backup vm \""+backupvmname+"\", using as source the snapshot \""+snname+"\" of vm \""+vmname+"\". Waiting for creation." )

# Wait for the backup vm to become ready:
backupvmserv = vmsserv.vm_service(backupvm.id)
timeoutstart = datetime.now()
while True :
    time.sleep(5)
    elapsedtime = datetime.now()-timeoutstart
    elapsedtimesecs = elapsedtime.total_seconds()
    backupvm = backupvmserv.get()
    if backupvm.status == types.VmStatus.DOWN :
        break
    elif elapsedtimesecs > clonedvmtimeoutsecs :
        errmessage = "the creation of backup vm \""+backupvmname+"\" from the snapshot \""+snname+"\" of the original vm \""+vmname+"\" has timed out after "+str(clonedvmtimeoutsecs)+" seconds. It's still possible vm creation finishes correctly on the cluster, later. Exiting."
        scriptlog.error( errmessage )
        statf = open(statusfile,"w")
        statf.write("KO - "+errmessage)
        statf.close()
        engineconn.close()
        sys.exit(1)
    else :
        scriptlog.info( "the status of cloned vm "+backupvmname+" is still \""+str(backupvm.status)+"\", waiting until it's \"down\". Elapsed time: "+str(int(elapsedtimesecs))+" seconds, timeout triggers after "+str(clonedvmtimeoutsecs)+" seconds." )
scriptlog.info( "backup vm \""+backupvmname+"\", was successfully created from the snapshot \""+snname+"\" of vm \""+vmname+"\"." )

# Unplug backup vm nics:
clonedvmnicsserv = backupvmserv.nics_service()
for nic in clonedvmnicsserv.list():
    nicid = nic.id
    clonedvmnicsserv.nic_service(nicid).update(
    nic = types.Nic(
            id = nicid,
            plugged = False
        )
    )
scriptlog.info( "requested setting of vnics as unplugged for backup vm \""+backupvmname+"\"." )

# Remove delete protection, if present, from backup vm (will be moved to export domain)
noprotectvar = types.Vm(
   delete_protected = False
)
backupvmserv.update(noprotectvar)

# Request removal of temporary snapshot used to generate cloned vm:
snapserv = snapsserv.snapshot_service(backsnap.id)
snapserv.remove()
scriptlog.info( "requested removal of temporary snapshot \""+snname+"\" of vm \""+backupvmname+"\"." )

# Move backup cloned vm to export storage domain:
backupvmserv.export_to_export_domain( storage_domain = stordom )
scriptlog.info( "requested export of backup vm \""+backupvmname+"\" to \""+stordomname+"\" storage domain." )
timeoutstart = datetime.now()
time.sleep(10)
while True:
    elapsedtime = datetime.now()-timeoutstart
    elapsedtimesecs = elapsedtime.total_seconds()
    exportvms = stordomserv.vms_service().list()
    exportvm = next(
        (curexpvm for curexpvm in exportvms if curexpvm.name == backupvmname),
        None
    )
    if exportvm is None:
        if elapsedtimesecs > backexprtimeoutsecs :
            errmessage = "the export to storage domain \""+stordomname+"\" of the backup vm \""+backupvmname+"\" has timed out after "+str(backexprtimeoutsecs)+" seconds. Exiting."
            scriptlog.error( errmessage )
            statf = open(statusfile,"w")
            statf.write("KO - "+errmessage)
            statf.close()
            engineconn.close()
            sys.exit(1)
        else:
            scriptlog.info( "the export to storage domain \""+stordomname+"\" of the backup vm \""+backupvmname+"\" isn't done yet. Waiting. Elapsed time: "+str(int(elapsedtimesecs))+" seconds, timeout triggers after "+str(int(backexprtimeoutsecs))+" seconds." )
            time.sleep(15)
    else:
        break
scriptlog.info( "backup vm \""+backupvmname+"\" was exported to \""+stordomname+"\" storage domain." )
backupvmserv.remove()
scriptlog.info( "requested removal of temporary vm \""+backupvmname+"\" from original vm storage domain, because it was exported to the \""+stordomname+"\" storage domain." )

# Delete obsolete backups:
scriptlog.info( "creation of new backup was done. Starting search for obsolete backups to remove." )
vmprefix = backupvmprefix+"-"+vmname+"-"
datesuffix = re.compile('-\d{8}_\d{6}$')
currentdate = datetime.now()
exportvms = stordomserv.vms_service().list()
foundvms = len(exportvms)
exportvmsthis = []
for x in range (0 , foundvms):
    curvm=exportvms[x]
    if curvm.name.startswith(vmprefix) :
        exportvmsthis.append(exportvms[x])
exportvms = exportvmsthis
def listedVmName(elem):
    return elem.name
exportvms.sort(key=listedVmName)
foundvms = len(exportvms)
maxremovals = foundvms - minbackupvms
removalnum = 0
if maxremovals < 0: maxremovals = 0
scriptlog.info( "number of found backup vms: "+str(foundvms)+", minimum number of backup vms: "+str(minbackupvms)+". A maximum of "+str(maxremovals)+" backup vms will be removed, each backup will be removed only if its age is greater than retention time, which is "+str(backupretentiondays)+" days." )
scriptlog.info( "backup vms removed till now: "+str(removalnum) )
for x in range (0 , foundvms):
    curvm = exportvms[x]
    scriptlog.info( "searching obsolete backup vms, iteration "+str(x+1)+" - found exported backup vm \""+exportvms[x].name+"\". Analyzing:" )
    vmnamesuffix = datesuffix.findall(curvm.name)[0]
    vmdate = datetime.strptime(vmnamesuffix, "-%Y%m%d_%H%M%S")
    scriptlog.info( "vm name: \""+curvm.name+"\", vm suffix: \""+vmnamesuffix+"\", parsed date: "+vmdate.strftime("%Y-%m-%d %H:%M:%S") )
    backupage = currentdate - vmdate
    backupagedays = backupage.total_seconds() / 86400
    scriptlog.info( "backup age in days: "+str(backupagedays) )
    if (removalnum < maxremovals) and (backupagedays > backupretentiondays):
        scriptlog.info( "removal of the exported backup vm \""+curvm.name+"\" will be requested because it is "+str(backupagedays)+" days old and the maximum age is "+str(backupretentiondays)+" days." )
        obsvmserv = stordomserv.vms_service().vm_service(curvm.id)
        obsvmserv.remove()
        removalnum += 1
        scriptlog.info( "backup vms removed till now: "+str(removalnum) )

# Write status of backup and exit:
statf = open(statusfile,"w")
statf.write('OK')
statf.close()
engineconn.close()
scriptlog.info( "script finished. Exiting." )
sys.exit(0)

