#!/bin/bash

#
# Copyright (c) 2020-2021 Marco Napolitano
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

cd  /opt/ovicbackup/status/
for statfile in $(ls -1 *.status)
do
  if [ $(grep -iv '^ok' ${statfile} | wc -w) -gt 0 ]
  then
    kill -0 $(grep -i '^pid' ${statfile} | awk -F' ' '{print $1}' | awk -F':' '{print $2}') 2>/dev/null
    if [ $? -eq 0 ]
    then
      if [ $(grep -i 'longrun' ${statfile} | wc -l) -gt 0 ]
      then
        echo -n " - ${statfile}: process running for long  "
      elif [ $(find ${statfile} -mmin +120 | grep -i '^ovicrbdsnapshot' | wc -l) -gt 0 ]
      then
        echo -n " LONGRUN" >> ${statfile}
        echo -n " - ${statfile}: process running for long  "
      elif [ $(find ${statfile} -mmin +900 | grep -i '^ovicrbdbackup' | wc -l) -gt 0 ]
      then
        echo -n " LONGRUN" >> ${statfile}
        echo -n " - ${statfile}: process running for long  "
      elif [ $(find ${statfile} -mmin +2220 | grep -i '^ovicvmbackup' | wc -l) -gt 0 ]
      then
        echo -n " LONGRUN" >> ${statfile}
        echo -n " - ${statfile}: process running for long  "
      fi
    elif [ $(grep -i '^pid' ${statfile} | wc -l ) -gt 0 ]
    then
      echo -n " - ${statfile}: process disappeared (crashed?)  "
    else
      echo -n " - ${statfile}: $(tail -n1 ${statfile})  "
    fi
  fi
done
exit 0

