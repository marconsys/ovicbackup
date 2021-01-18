oViCbackup
================
A set of backup and snapshot scripts for oVirt/RHV virtual machines and for Ceph RBD volumes.

## Copyright
Copyright (c) 2020-2021 Marco Napolitano<br/>
The author is Marco Napolitano, email: mannysys-AaaaT-outlook.com put at sign instead of -AaaaT-<br/>
The content of the repository is licensed under Apache License, available at: http://www.apache.org/licenses/LICENSE-2.0

## Disclaimer
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Description
This repository contains a set of backup and snapshot scripts for oVirt virtual machines and Ceph volumes.<br/>
The main script is made to be called directly, the others are made just to be in turn called by the main scripts. Scripts are supposed to be run by a local user called "ovicbackup".<br/>
The script to be called directly is:<br/>
ovicbackup.sh<br/>
Be sure to install ovirt python components to use ovirt scripts, to correctly install and configure ceph client to use ceph scripts, to correctly install backy2 software as python module for the "ovicbackup" user, that runs the script.<br/>
Examples of script scheduling in crontab:<br/>
<br/>
00 00 * * * /opt/ovicbackup/libexec/ovicbackup.sh ovicrbdsnapshot<br/>
30 00 * * 6 /opt/ovicbackup/libexec/ovicbackup.sh ovicrbdbackup<br/>
30 00 * * 7 /opt/ovicbackup/libexec/ovicbackup.sh ovicvmbackup<br/>
<br/>
Secondary scripts are in turn called based on the argument passed to ovicbackup.sh, which is one of the three shown in the example crontab. Then operations are done on targets defined in lists:<br/>
/opt/ovicbackup/lists/ovicrbdsnapshot.list - list of ceph rbd volumes to be snapshotted<br/>
/opt/ovicbackup/lists/ovicrbdbackup.list - list of ceph rbd volumes to be cloned for backup<br/>
/opt/ovicbackup/lists/ovicvmbackup.list - list of ovirt/rhv vms to be cloned and exported for backup<br/>
<br/>
There is also the script:<br/>
ovicbackupstatus.sh<br/>
It gives some output if it finds anomailes inside ".status" files; it gives no output if no anomalies are found: so it's useful for monitoring, suitable for monitoring tools.<br/>
<br/>
Directory structure for these script on the machine that runs them, is as follows:<br/>
/opt/ovicbackup/libexec/   ->   scripts<br/>
/opt/ovicbackup/lists/     ->   list files<br/>
/opt/ovicbackup/etc/       ->   config files<br/>
/opt/ovicbackup/log/       ->   log files<br/>
/opt/ovicbackup/status/    ->   status files<br/>
/opt/ovicbackup/tmp/       ->   temporary files<br/>
<br/>

