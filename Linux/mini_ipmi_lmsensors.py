#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

binPath = r'sensors'
#binPath = r'/usr/bin/sensors'   # if 'sensors' isn't in PATH

# path to second send script
senderPyPath = r'/etc/zabbix/scripts/sender_wrapper.py'

# path to zabbix agent configuration file
agentConf = r'/etc/zabbix/zabbix_agentd.conf'

senderPath = r'zabbix_sender'
#senderPath = r'/usr/bin/zabbix_sender'

timeout = '80'         # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                       # this setting MUST be lower than 'Update interval' in discovery rule
fallbackTjMax = '85'
fallbackVcore = '1.35'
fallbackVtt = '1.1'

# Following settings brings (almost) no overhead. Use 'no' to disable unneeded data.
gatherVoltages = 'yes'
gatherBoardFans = 'yes'
gatherBoardTemp = 'yes'
gatherGpuData = 'yes'
gatherCpuData = 'yes'

## End of configuration ##

import sys
import subprocess
import re
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3)


def getOutput():
    try:
        from subprocess import DEVNULL   # for python versions greater than 3.3, inclusive
    except:
        import os
        DEVNULL = open(os.devnull, 'w') # for 3.0-3.2, inclusive

    p = None
    try:
        p = subprocess.check_output([binPath, '-u'], universal_newlines=True, stderr=DEVNULL)
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

    pSplit = p.strip()
    pSplit = pSplit.split('\n\n')
#    for i in pSplit: print(i, '\n')   # DEBUG

    return error, pSplit


def getVoltages():
    sender = []
    json = []

    for v in pOut:
        if 'Adapter: PCI adapter' in v:   # we dont need GPU voltages
            continue

        voltage = re.findall(r'(.+):\n(?:\s+)?in(\d+)_input:\s+(\d+\.\d+)', v, re.I)
        if voltage:
            for i in voltage:
                if re.search('Vcore', i[0], re.I):
                    sender.append('%s mini.brd.vlt[cpuVcore] "%s"' % (host, i[2]))
                    json.append({'{#VCORE}':'cpuVcore'})   # hardcoded because of zabbix stubbornness

                    vcoreRe = re.search('in' + i[1] + r'_max:\s+(\d+\.\d+)', v, re.I)
                    if vcoreRe:
                        vcore = vcoreRe.group(1)
                    else:
                        vcore = fallbackVcore

                    sender.append('%s mini.brd.info[vcoreMax] "%s"' % (host, vcore))
    
                elif re.search('VBAT', i[0], re.I):
                    sender.append('%s mini.brd.vlt[VBat] "%s"' % (host, i[2]))
                    json.append({'{#VBAT}':'VBat'})
 
                elif re.search('3VSB|VSB3V|Standby \+3\.3V|3V_SB', i[0], re.I):
                    sender.append('%s mini.brd.vlt[VSB3V] "%s"' % (host, i[2]))
                    json.append({'{#VSB3V}':'VSB3V'})
 
                elif re.search('3VCC|VCC3V', i[0], re.I):
                    sender.append('%s mini.brd.vlt[VCC3V] "%s"' % (host, i[2]))
                    json.append({'{#VCC3V}':'VCC3V'})
        
                elif re.search('AVCC', i[0], re.I):
                    sender.append('%s mini.brd.vlt[AVCC] "%s"' % (host, i[2]))
                    json.append({'{#VAVCC}':'AVCC'})
        
                elif re.search('VTT', i[0], re.I):
                    sender.append('%s mini.brd.vlt[VTT] "%s"' % (host, i[2]))
                    json.append({'{#VTT}':'VTT'})
     
                    vttRe = re.search('in' + i[1] + r'_max:\s+(\d+\.\d+)', v, re.I)
                    if vttRe:
                        vtt = vttRe.group(1)
                    else:
                        vtt = fallbackVtt

                    sender.append('%s mini.brd.info[vttMax] "%s"' % (host, vtt))
 
                elif re.search('\+3\.3 Voltage', i[0], re.I):
                    sender.append('%s mini.brd.vlt[p3.3V] "%s"' % (host, i[2]))
                    json.append({'{#P33V}':'p3.3V'})
     
                elif re.search('\+5 Voltage', i[0], re.I):
                    sender.append('%s mini.brd.vlt[p5V] "%s"' % (host, i[2]))
                    json.append({'{#P5V}':'p5V'})
     
                elif re.search('\+12 Voltage', i[0], re.I):
                    sender.append('%s mini.brd.vlt[p12V] "%s"' % (host, i[2]))
                    json.append({'{#P12V}':'p12V'})
 
                sender.append('%s mini.brd.vlt[%s] "%s"' % (host, i[1], i[2]))   # static items for graph, could be duplicate

            break   # as safe as possible

    return sender, json


def getBoardFans():
    sender = []
    json = []

    for i in pOut:
        if 'Adapter: PCI adapter' in i:   # we dont need GPU fans
            continue
 
        fans = re.findall(r'(.+):\n(?:\s+)?fan(\d+)_input:\s+(\d+)', i, re.I)
        if fans:
            for f in fans:
                # only create LLD when speed is not zero, BUT always send values including zero (prevents false triggering)
                sender.append('%s mini.brd.fan[%s,rpm] "%s"' % (host, f[1], f[2]))
                if f[2] != '0':
                    json.append({'{#BRDFANNAME}':f[0].strip(), '{#BRDFANNUM}':f[1]})
 
            break

    return sender, json


def getBoardTemp():
    sender = []
    json = []

    for i in pOut:
        if 'Adapter: PCI adapter' in i:   # we dont need GPU temps
            continue
 
        temps = re.findall(r'((?:CPU|GPU|MB|M/B|AUX|Ambient|Other|SYS|Processor).+):\n(?:\s+)?temp(\d+)_input:\s+(\d+)', i, re.I)
        if temps:
            for t in temps:
                sender.append('%s mini.brd.temp[%s] "%s"' % (host, t[1], t[2]))
                json.append({'{#BRDTEMPNAME}':t[0].strip(), '{#BRDTEMPNUM}':t[1]})

            break

    return sender, json


def getGpuData():
    sender = []
    json = []

    gpuBlocks = -1
    allTemps = []
    for i in pOut:
        temp = re.search(r'(nouveau.+|nvidia.+)\n.+\n.+\n(?:\s+)?temp\d+_input:\s+(\d+)', i, re.I)
        if temp:
            gpuBlocks += 1
            allTemps.append(int(temp.group(2)))

            json.append({'{#GPU}':gpuBlocks})
            sender.append('%s mini.gpu.info[gpu%s,ID] "%s"' % (host, gpuBlocks, temp.group(1)))

            json.append({'{#GPUTEMP}':gpuBlocks})
            sender.append('%s mini.gpu.temp[gpu%s] "%s"' % (host, gpuBlocks, temp.group(2)))

    if gpuBlocks != -1:
        if allTemps:
            error = None
            sender.append('%s mini.gpu.temp[MAX] "%s"' % (host, max(allTemps)))
        else:
            error = 'NOGPUTEMPS'   # unreachable
    else:
        error = 'NOGPUS'

    return sender, json, error


def getCpuData():
    '''Note: certain cores can pose as different blocks making them separate cpus in zabbix.'''
    sender = []
    json = []

    cpuBlocks = -1   # first cpu will be '0'
    allTemps = []
    for i in pOut:   # for each block in output

        coreTempsRe = re.findall(r'Core(?:\s+)?(\d+)(?:\s+Temp)?:\n.+_input:\s+(\d+)', i, re.I | re.M)
        if coreTempsRe:
            cpuBlocks += 1   # you need to be creative to parse lmsensors

            json.append({'{#CPU}':cpuBlocks})
            sender.append('%s mini.cpu.info[cpu%s,ID] "%s"' % (host, cpuBlocks, i.splitlines()[0]))

            tempCrit = re.search(r'_crit:\s+(\d+)\.\d+', i, re.I)
            if tempCrit:
                tjMax = tempCrit.group(1)
            else:
                tjMax = fallbackTjMax

            sender.append('%s mini.cpu.info[cpu%s,TjMax] "%s"' % (host, cpuBlocks, tjMax))

            previousCore = None
            cpuTemps = []
            for c in coreTempsRe:
                if previousCore == c[0]:
                    continue   # some cores have same number - ignore them
                previousCore = c[0]

                cpuTemps.append(int(c[1]))
                allTemps.append(int(c[1]))
                sender.append('%s mini.cpu.temp[cpu%s,core%s] "%s"' % (host, cpuBlocks, c[0], c[1]))
                json.append({'{#CPUC}':cpuBlocks, '{#CORE}':c[0]})

            sender.append('%s mini.cpu.temp[cpu%s,MAX] "%s"' % (host, cpuBlocks, max(cpuTemps)))

    if cpuBlocks != -1:
        if allTemps:
            error = None
            sender.append('%s mini.cpu.temp[MAX] "%s"' % (host, max(allTemps)))
        else:
            error = 'NOCPUTEMPS'
    else:
        error = 'NOCPUS'

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

        if gatherVoltages == 'yes':
            getVoltages_Out = getVoltages()
            senderData.extend(getVoltages_Out[0])
            jsonData.extend(getVoltages_Out[1])

        if gatherBoardFans == 'yes':
            getBoardFans_Out = getBoardFans()
            senderData.extend(getBoardFans_Out[0])
            jsonData.extend(getBoardFans_Out[1])

        if gatherBoardTemp == 'yes':
            getBoardTemp_Out = getBoardTemp()
            senderData.extend(getBoardTemp_Out[0])
            jsonData.extend(getBoardTemp_Out[1])

        if gatherGpuData == 'yes':
            getGpuData_Out = getGpuData()
            senderData.extend(getGpuData_Out[0])
            jsonData.extend(getGpuData_Out[1])
            if getGpuData_Out[2]:
                statusC = 'gpu_err'
                # mini.cpu.info[ConfigStatus] is used to track configuration states including cpu and gpu:
                senderData.append(host + ' mini.cpu.info[ConfigStatus] "' + getGpuData_Out[2] + '"')   # NOGPUS, NOGPUTEMPS

        if gatherCpuData == 'yes':
            getCpuData_Out = getCpuData()
            senderData.extend(getCpuData_Out[0])
            jsonData.extend(getCpuData_Out[1])
            if getCpuData_Out[2]:
                statusC = 'cpu_err'
                senderData.append('%s mini.cpu.info[ConfigStatus] "%s"' % (host, getCpuData_Out[2]))   # NOCPUS, NOCPUTEMPS

    if not statusC:
        senderData.append('%s mini.cpu.info[ConfigStatus] "%s"' % (host, getOutput_Out[0]))   # OS_NOCMD, OS_ERROR, UNKNOWN_EXC_ERROR, CONFIGURED

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    processData(senderData, jsonData, agentConf, senderPyPath, senderPath, timeout, host, link)
