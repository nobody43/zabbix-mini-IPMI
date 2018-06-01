#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

binPath = r'/sbin/sysctl'

# path to second send script
senderPyPath = r'/usr/local/etc/zabbix/scripts/sender_wrapper.py'

# path to zabbix agent configuration file
agentConf = r'/usr/local/etc/zabbix3/zabbix_agentd.conf'

senderPath = r'zabbix_sender'
#senderPath = r'/usr/bin/zabbix_sender'

timeout = '80'         # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                       # this setting MUST be lower than 'Update interval' in discovery rule
tjMax = '85'

## End of configuration ##

import sys
import subprocess
import re
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3)


def getOutput():
    p = None
    try:
        p = subprocess.check_output([binPath, 'dev.cpu'], universal_newlines=True)
    except OSError as e:
        if e.args[0] == 2:
            error = 'OS_NOCMD'
        else:
            error = 'OS_ERROR'
            if sys.argv[1] == 'getverb':
                raise
    except Exception as e:
        error = 'UNKNOWN_EXC_ERROR'

        if sys.argv[1] == 'getverb':
            raise

        try:
            p = e.output
        except:
            pass
    else:
        error = 'CONFIGURED'

    return error, p


def getCpuData():
    '''Can work unexpectedly with multiple CPUs.'''
    sender = []
    json = []

    temp = re.findall(r'dev\.cpu\.(\d+)\.temperature:\s+(\d+)', pOut, re.I)
    if temp:
        error = None
        json.append({'{#CPU}':'0'})

        allTemps = []
        for i in temp:
            allTemps.append(i[1])
            sender.append('%s mini.cpu.temp[cpu0,core%s] "%s"' % (host, i[0], i[1]))
            json.append({'{#CPUC}':'0', '{#CORE}':i[0]})

        sender.append('%s mini.cpu.info[cpu0,TjMax] "%s"' % (host, tjMax))
        sender.append('%s mini.cpu.temp[cpu0,MAX] "%s"' % (host, max(allTemps)))
        sender.append('%s mini.cpu.temp[MAX] "%s"' % (host, max(allTemps)))

    else:
        error = 'NOCPUTEMPS'

    return sender, json, error


if __name__ == '__main__':
    fail_ifNot_Py3()

    host = '"' + sys.argv[2] + '"'   # hostname
    senderData = []
    jsonData = []

    getOutput_Out = getOutput()

    statusC = None
    if getOutput_Out[1]:   # process output
        pOut = getOutput_Out[1]

        getCpuData_Out = getCpuData()
        senderData.extend(getCpuData_Out[0])
        jsonData.extend(getCpuData_Out[1])
        if getCpuData_Out[2]:
            statusC = 'cpu_err'
            senderData.append('%s mini.cpu.info[ConfigStatus] "%s"' % (host, getCpuData_Out[2]))

    if not statusC:
        senderData.append('%s mini.cpu.info[ConfigStatus] "%s"' % (host, getOutput_Out[0]))   # OS_NOCMD, OS_ERROR, UNKNOWN_EXC_ERROR, CONFIGURED

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    processData(senderData, jsonData, agentConf, senderPyPath, senderPath, timeout, host, link)

