#!/bin/bash

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

# Declarations:
basepath="/opt/ovicbackup"
scriptname="ovicbackup"
pythonexecutable="/bin/python"
scriptlogfile="${scriptname}.log"
scriptlogpath="${basepath}/log/${scriptlogfile}"
statuspathprefix="${basepath}/status/${scriptname}-"
statuspathsuffix=".status"
statuspath=""
calledscriptexists=false
waitstep=300
waitnum=100


# Logging functions:
scriptLogInfoList () {
  scriptLogInfo "the list contains the following values:"
  for entry in $(cat ${1})
  do
    scriptLogInfo "    ${entry}"
  done
  scriptLogInfo "the list is finished."
}

scriptLogInfo () {
  echo -e "[$(date +"%F %T"),$(date +"%N" | cut -c -3)] PID: $$ - INFO: $1" >> ${scriptlogpath}
}

scriptLogErro () {
  echo -e "[$(date +"%F %T"),$(date +"%N" | cut -c -3)] PID: $$ - ERROR: $1" >> ${scriptlogpath}
}

# Script running fuctions:
runScript () {
  scriptLogInfo "launching \"${1}\" with argument \"${2}\"."
  ${pythonexecutable} ${1} ${2} >/dev/null 2>&1
  if [ $? -le 0 ]
  then
    scriptLogInfo "script \"${1}\" finished."
  else
    scriptLogErro "script \"${1}\" finished with exit status greather than 0."
  fi
}

runList () {
  if [[ -f ${2} && -r ${2} ]]
  then
    if [ $(cat ${2} | egrep -v "^[[:blank:]]*$" | wc -l) -gt 0 ]
    then
      scriptLogInfo "launching \"${1}\" following list file \"${2}\"."
      scriptLogInfoList ${2}
      for entry in $(cat ${2} | egrep -v "^[[:blank:]]*$")
      do
        runScript ${1} ${entry}
      done
    else
      scriptLogInfo "list \"${2}\" is empty."
    fi
  else
    exitWithError "can't read list file \"${2}\" for \"${1}\"."
  fi
}

# Exit with error function:
exitWithError () {
  scriptLogErro "${1}"
  echo "ERROR: ${1}"
  if ${calledscriptexists}
  then
    echo "ERROR: ${1}" > ${statuspath}
  fi
  exit 1
}

# Start:
scriptLogInfo "script started."

# Check arguments and run functions:
if [ $# -ne 1 ]
  then
    exitWithError "wrong number of arguments. One and only one argument should be given. Exiting."
  else
    calledscript=${1}
    calledscriptfile="${calledscript}.py"
    calledscriptpath="${basepath}/libexec/${calledscriptfile}"
    calledscriptlist="${basepath}/lists/${calledscript}.list"
    calledscriptstatus="${basepath}/status/${calledscript}*.status"
    scriptLogInfo "script was launched with argument \"${1}\", so script path will be: \"${calledscriptpath}\""
    scriptLogInfo "script was launched with argument \"${1}\", so script list will be: \"${calledscriptlist}\""
    statuspath="${statuspathprefix}${calledscript}${statuspathsuffix}"
    rm -f ${statuspath} 2>/dev/null
    if [[ -f ${calledscriptpath} && -r ${calledscriptpath} && -x ${calledscriptpath} ]]
    then
      calledscriptexists=true
      waitednum=0
      while [ ${waitednum} -le ${waitnum} ]
      do
        if [ $(grep -i '^pid' ${calledscriptstatus} | wc -l) -gt 0 ]
        then
          scriptLogInfo "waiting for other ${calledscript} run to finish."
          sleep ${waitstep}
          waitednum=$((waitednum+1))
        else
          waitednum=$((waitnum+1))
        fi
      done
      if [ $(grep -i '^pid' ${calledscriptstatus} | wc -l) -gt 0 ]
      then
         exitWithError "other ${calledscript} launch still running, or crashed. Check status files. Nothing done, exiting."
      fi
      runList ${calledscriptpath} ${calledscriptlist}
    else
      exitWithError "the script \"${calledscriptpath}\" was not found or is not executable. Exiting."
    fi
fi

# End:
scriptLogInfo "script finished. Exiting."
exit 0
