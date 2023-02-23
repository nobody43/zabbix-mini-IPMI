#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

BIN_PATH = r'/sbin/sysctl'

# path to second send script
SENDER_WRAPPER_PATH = r'/usr/local/etc/zabbix/scripts/sender_wrapper.py'

# path to zabbix agent configuration file
AGENT_CONF_PATH = r'/usr/local/etc/zabbix3/zabbix_agentd.conf'

SENDER_PATH = r'zabbix_sender'
#SENDER_PATH = r'/usr/bin/zabbix_sender'

DELAY = '50'         # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                     # this setting MUST be lower than 'Update interval' in discovery rule
TJMAX = '70'

## End of configuration ##

import sys
import subprocess
import re
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3)

HOST = sys.argv[2]


def getOutput(binPath_):

    p = None
    try:
        p = subprocess.check_output([binPath_, 'dev.cpu'], universal_newlines=True)
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


def getCpuData(pOut_):
    '''Can work unexpectedly with multiple CPUs.'''
    sender = []
    json = []

    tempRe = re.findall(r'dev\.cpu\.(\d+)\.temperature:\s+(\d+)', pOut_, re.I)
    if tempRe:
        error = None
        json.append({'{#CPU}':'0'})

        allTemps = []
        for num, val in tempRe:
            allTemps.append(val)
            sender.append('"%s" mini.cpu.temp[cpu0,core%s] "%s"' % (HOST, num, val))
            json.append({'{#CPUC}':'0', '{#CORE}':num})

        sender.append('"%s" mini.cpu.info[cpu0,TjMax] "%s"'   % (HOST, TJMAX))
        sender.append('"%s" mini.cpu.temp[cpu0,MAX] "%s"'     % (HOST, max(allTemps)))
        sender.append('"%s" mini.cpu.temp[MAX] "%s"'          % (HOST, max(allTemps)))

    else:
        error = 'NOCPUTEMPS'

    return sender, json, error


if __name__ == '__main__':

    fail_ifNot_Py3()

    senderData = []
    jsonData = []

    p_Output = getOutput(BIN_PATH)
    pRunStatus = p_Output[0]
    pOut = p_Output[1]

    errors = None
    if pOut:
        getCpuData_Out = getCpuData(pOut)
        cpuErrors = getCpuData_Out[2]
        senderData.extend(getCpuData_Out[0])
        jsonData.extend(getCpuData_Out[1])
        if cpuErrors:
            errors = 'cpu_err'
            senderData.append('"%s" mini.cpu.info[ConfigStatus] "%s"' % (HOST, cpuErrors))

    if not errors:
        senderData.append('"%s" mini.cpu.info[ConfigStatus] "%s"' % (HOST, pRunStatus))   # OS_NOCMD, OS_ERROR, UNKNOWN_EXC_ERROR, CONFIGURED

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    sendStatusKey = 'mini.cpu.info[SendStatus]'
    processData(senderData, jsonData, AGENT_CONF_PATH, SENDER_WRAPPER_PATH, SENDER_PATH, DELAY, HOST, link, sendStatusKey)

