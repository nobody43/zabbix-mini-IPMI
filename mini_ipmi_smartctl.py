#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

checkStandby = 'no'   # whether to check disks in STANDBY mode or not, 'yes' or 'no'
                      # if 'Update interval' is less than OS setting for STANDBY disks - it will never enter this state

ctlPath = r'smartctl'
#ctlPath = r'C:\Program Files\smartmontools\bin\smartctl.exe'       # if smartctl isn't in PATH
#ctlPath = r'/usr/local/sbin/smartctl'

# path to second send script
senderPyPath = r'/etc/zabbix/scripts/sender_wrapper.py'             # Linux
#senderPyPath = r'C:\zabbix-agent\scripts\sender_wrapper.py'        # Win
#senderPyPath = r'/usr/local/etc/zabbix/scripts/sender_wrapper.py'  # BSD

# path to zabbix agent configuration file
agentConf = r'/etc/zabbix/zabbix_agentd.conf'                       # Linux
#agentConf = r'C:\zabbix_agentd.conf'                               # Win
#agentConf = r'/usr/local/etc/zabbix3/zabbix_agentd.conf'           # BSD

senderPath = r'zabbix_sender'                                       # Linux, BSD
#senderPath = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'        # Win

timeout = '80'   # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                 # this setting MUST be lower than 'Update interval' in discovery rule

# manually provide disk list or RAID configuration if needed
diskListManual = []
# like this:
#diskListManual = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

## End of configuration ##

import sys
import subprocess
import re
from shlex import split
from sender_wrapper import (readConfig, processData, replaceStr, fail_ifNot_Py3)


def listDisks():
    '''Determines available disks. Can be skipped.'''
    try:
        p = subprocess.check_output([ctlPath, '--scan'], universal_newlines=True)   # scan the disks
        error = ''
    except OSError as e:
        p = ''

        if e.args[0] == 2:
            error = 'SCAN_OS_NOCMD'
        else:
            error = 'SCAN_OS_ERROR'
    except Exception as e:
        try:   # extra safe
            p = e.output
        except:
            p = ''
        error = 'SCAN_UNKNOWN_ERROR'
        if sys.argv[1] == 'getverb':
            raise

    disks = re.findall(r'^(/dev/[^ ]+)', p, re.M)   # determine full device names

    return error, disks


def isStandby(dS):
    '''Checks whether disk is in STANDBY mode.
       No exceptions properly handled there - parent handling is sufficent.'''

    try:
        pS = subprocess.check_output([ctlPath, '--nocheck', 'standby', '-i'] + split(dS), universal_newlines=True)
    except Exception as eS:
        try:
            pS = eS.output
        except:
            pS = ''

    if 'evice is in STANDBY mode' in pS:
        return 1
    else:
        return None


def getDiskTempA(dA):
    '''Tries to get temperature from provided disk via regular -A command.
       No exceptions properly handled there - parent handling is sufficent.
       Also contains SAS fallback.'''

    try:
        pA = subprocess.check_output([ctlPath, '-A'] + split(dA), universal_newlines=True)
    except Exception as eA:
        try:
            pA = eA.output
        except:
            pA = ''

    tempA = re.search('Temperature_Celsius\s+\w+\s+\d+\s+\d+\s+\d+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)\s', pA, re.I)
    tempSAS = re.search('Current\s+Drive\s+Temperature:\s+(\d+)\s+', pA, re.I)

    if tempA:
        if sys.argv[1] == 'getverb': print('getDiskTempA called:', tempA.group(1))   # DEBUG
        resultA = tempA.group(1)
    elif tempSAS:
        if sys.argv[1] == 'getverb': print('getDiskTempSAS called:', tempSAS.group(1))   # DEBUG
        resultA = tempSAS.group(1)
    else:
        if sys.argv[1] == 'getverb': print('getDiskTempA called: None')   # DEBUG
        resultA = None

    return resultA


def getDisksTempSCT():
    '''Tries to get temperature from every disk provided in list via SCT command.
       Also calculates maximum temperature among all disks.'''
    temperatures = []
    sender = []

    globalError = ''   # intended to change once in loop
    for d in diskList:
        dR = replaceStr(d)   # sanitize the item key

        if not checkStandby == 'yes':
            if isStandby(d):
                sender.append(host + ' mini.disk.info[' + dR + ',DriveStatus] "STANDBY"')
                continue   # do not try to access current disk if its in STANDBY mode

        p = ''
        localError = ''
        try:
            # take string from 'diskList', make arguments from it and append to existing command, then run it
            p = subprocess.check_output([ctlPath, '-l', 'scttempsts'] + split(d), universal_newlines=True)
        except OSError as e:
            if e.args[0] == 2:
                globalError = 'D_OS_NOCMD'
            else:
                globalError = 'D_OS_ERROR'
                if sys.argv[1] == 'getverb':
                    raise

            break   # configuration error
        except subprocess.CalledProcessError as e:   # handle process-specific errors
            if not e.args:   # unnecessary for python3?
                sender.append('%s mini.disk.info[%s,DriveStatus] "UNKNOWN_RESPONSE"' % (host, dR))
                continue
            elif e.args[0] == 1 or e.args[0] == 2:   # non-fatal disk error codes are not a concern for temperature monitoring script
                sender.append(host + ' mini.disk.info[' + dR + ',DriveStatus] "ERR_CODE_' + str(e.args[0]) + '"')
                continue   # continue to the next disk on fatal error

            p = e.output   # substitute output even on error, so it can be processed further
        except Exception as e:
            localError = 'UNKNOWN_EXC_ERROR'

            if sys.argv[1] == 'getverb':
                raise

            try:
                p = e.output
            except:
                p = ''

        temp = re.search(r'Current\s+Temperature:\s+(\d+)\s+Celsius', p, re.I)

        if temp:
            tempResult = temp.group(1)
        else:   # if nothing was found - try regular SMART command
            getDiskTempA_Out = getDiskTempA(d)
            if getDiskTempA_Out:
                tempResult = getDiskTempA_Out
            else:
                tempResult = ''
                localError = 'NO_TEMP'

        if tempResult != '':
            sender.append(host + ' mini.disk.temp[' + dR + '] ' + tempResult)
            temperatures.append(int(tempResult))

        if localError == '':
            sender.append(host + ' mini.disk.info[' + dR + ',DriveStatus] "PROCESSED"')   # no trigger assigned, fallback value
        elif localError == 'NO_TEMP':
            sender.append(host + ' mini.disk.info[' + dR + ',DriveStatus] "NO_TEMP"')
        else:
            sender.append(host + ' mini.disk.info[' + dR + ',DriveStatus] "UNKNOWN_ERROR_ON_PROCESSING"')
 
    if temperatures:
        sender.append(host + ' mini.disk.temp[MAX] ' + str(max(temperatures)))
    elif globalError == '':   # if no temperatures were discovered and globalError was not set
        globalError = 'NOTEMPS'

    return globalError, sender


if __name__ == '__main__':
    fail_ifNot_Py3()

    host = '"' + sys.argv[2] + '"'
    jsonData = []

    if not diskListManual:   # if manual list is not provided
        listDisks_Out = listDisks()   # scan the disks

        scanConfigError = listDisks_Out[0]   # SCAN_OS_NOCMD, SCAN_OS_ERROR, SCAN_UNKNOWN_ERROR
        diskList = listDisks_Out[1]
    else:
        scanConfigError = ''
        diskList = diskListManual   # or just use manually provided settings

    if diskList:
        getDisksTempSCT_Out = getDisksTempSCT()

        diskConfigError = getDisksTempSCT_Out[0]   # D_OS_NOCMD, D_OS_ERROR, NOTEMPS, UNKNOWN_EXC_ERROR
        senderData = getDisksTempSCT_Out[1]
    else:
        diskConfigError = 'NODISKS'
        senderData = []

    if scanConfigError != '':
        senderData.append(host + ' mini.disk.info[ConfigStatus] "' + scanConfigError + '"')   # takes precedence
    elif diskConfigError != '':
        senderData.append(host + ' mini.disk.info[ConfigStatus] "' + diskConfigError + '"')   # on mixed errors
    else:
        senderData.append(host + ' mini.disk.info[ConfigStatus] "CONFIGURED"')   # signals that client host is configured

    for d in diskList:
        dR = replaceStr(d)
        jsonData.append({'{#DISK}':dR})   # available disks must always be populated to LLD

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    processData(senderData, jsonData, agentConf, senderPyPath, senderPath, timeout, host, link)

