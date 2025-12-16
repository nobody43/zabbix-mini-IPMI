#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# SPDX-License-Identifier: GPL-3.0-only

BIN_PATH = r'sensors'   # runs with '-u'
#BIN_PATH = r'/usr/bin/sensors'   # if 'sensors' isn't in PATH

# path to second send script
SENDER_WRAPPER_PATH = r'/etc/zabbix/scripts/sender_wrapper.py'

# path to zabbix agent configuration file
AGENT_CONF_PATH = r'/etc/zabbix/zabbix_agentd.conf'

SENDER_PATH = r'zabbix_sender'
#SENDER_PATH = r'/usr/bin/zabbix_sender'

FALLBACK_TJMAX = '70'

# Following settings brings (almost) no overhead. True or False
GATHER_VOLTAGES     = True
GATHER_FANS         = True
GATHER_BOARD_TEMPS  = True
GATHER_GPU_DATA     = True
GATHER_CPU_DATA     = True

VOLTAGE_REGEXPS_KEYS_AND_MACRO = (
    ( 'Vcore',                               'cpuVcore', '{#VCORE}'),
    ( 'VBAT',                                'VBat',     '{#VBAT}'),
    (r'3VSB|VSB3V|Standby \+3\.3V|3V_SB',    'VSB3V',    '{#VSB3V}'),
    ( '3VCC|VCC3V',                          'VCC3V',    '{#VCC3V}'),
    ( 'AVCC',                                'AVCC',     '{#AVCC}'),
    ( 'VTT',                                 'VTT',      '{#VTT}'),
    (r'\+3\.3 Voltage',                      'p3.3V',    '{#p3.3V}'),
    (r'\+5 Voltage',                         'p5V',      '{#p5V}'),
    (r'\+12 Voltage',                        'p12V',     '{#p12V}'),
)

# re.I | re.M ; (core_ident, core_temperature)
CPU_REGEXPS = (
    (r'^Core(?:\s+)?(\d+):\n\s+temp\d+_input:\s+(\d+)'),
    (r'^Core(\d+)\s+Temp:\n\s+temp\d+_input:\s+(\d+)'),
    (r'^Tdie:\n\s+temp(\d+)_input:\s+(\d+)'),
    (r'^Tccd(\d+):\n\s+temp\d+_input:\s+(\d+)'),
    (r'^k\d+temp-pci-\w+\nAdapter:\s+PCI\s+adapter\nTctl:\n\s+temp(\d+)_input:\s+(\d+)'),
    (r'^k\d+temp-pci-\w+\nAdapter:\s+PCI\s+adapter\ntemp(\d+):\n\s+temp\d+_input:\s+(\d+)'),
    (r'^cpu_thermal-virtual-\w+\nAdapter: Virtual device\ntemp(\d+):\n\s+temp\d+_input:\s+(\d+)\.'),
    (r'^bigcore\d+_thermal-virtual-\w+\nAdapter: Virtual device\ntemp(\d+):\n\s+temp\d+_input:\s+(\d+)\.'),
)

# re.I | re.M ; (gpu_ident, temperature)
GPU_REGEXPS = (
    (r'^(radeon-.+)(?:\n.*?)*\ntemp\d+:\n\s+temp\d+_input:\s+(\d+)\.'),
    (r'^(amdgpu-.+)(?:\n.*?)*\nedge:\n\s+temp\d+_input:\s+(\d+)\.'),
    (r'^(nouveau-.+)(?:\n.*?)*\ntemp\d+:\n\s+temp\d+_input:\s+(\d+)\.'),
    (r'^(gpu_thermal-virtual-.+)(?:\n.*?)*\ntemp\d+:\n\s+temp\d+_input:\s+(\d+)\.'),
    (r'^(nvidia.+)(?:\n.*?)*(?:\s+)?temp\d+_input:\s+(\d+)'),
)

# re.I | re.M ; (temperature_ident, temperature)
BOARD_REGEXP = r'(^(?:Motherboard|Chipset|CPU|GPU|MB|M/B|AUX|Ambient|Other|SYS|Processor|PCH_.+_TEMP|PECI Agent)(?<!_MAX_TEMP).*):\n(?:\s+)?temp\d+_input:\s+(\d+)'

# re.I | re.M ; (fan_ident, rpm)
FAN_REGEXPS = (
    (r'(.+):\n(?:\s+)?fan\d+_input:\s+(\d+)'),
    (r'^(fan\d+):\n\s+fan\d+_input:\s+(\d+)\.'),
    (r'^pwmfan-isa-\w+\nAdapter: ISA adapter\n(pwm\d+):\n\s+pwm\d+:\s+(\d+)\.'),
)

IGNORED_SENSORS = (
    ('nct6791-isa-0290', 'AUXTIN3'),  # ignore 'AUXTIN3' on 'nct6791-isa-0290'
)

DELAY = '50'         # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                     # this setting MUST be lower than 'Update interval' in discovery rule

## End of configuration ##

import sys
import subprocess
import re
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3, removeQuotes, chooseDevnull, sanitizeStr)

 
def getOutput(binPath_):
    """Try to run 'sensors' to get the output"""
    DEVNULL = chooseDevnull()

    error = 'UNKNOWN_ERROR'
    p = None
    try:
        p = subprocess.check_output([binPath_, '-u'], universal_newlines=True, stderr=DEVNULL)

    except subprocess.CalledProcessError as e:
        if e.args[0] == 1:
            error = 'NO_SENSORS'

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

        if e:
            p = e.output

    else:
        error = 'CONFIGURED'

    return (error, p)


def getVoltages(pOut_):

    sender = []
    json = []

    for block in pOut_:
        if 'Adapter: PCI adapter' in block:   # we dont need GPU voltages
            continue

        voltagesRe = re.findall(r'(.+):\n(?:\s+)?in(\d+)_input:\s+(\d+\.\d+)', block, re.I)  # TODO: more precise
        if voltagesRe:
            for name, num, val in voltagesRe:
            
                for regexp, key, jsn in VOLTAGE_REGEXPS_KEYS_AND_MACRO:
                    if re.search(regexp, name, re.I):
                        sender.append('mini.brd.vlt[%s] "%s"' % (key, removeQuotes(val)))
                        json.append({jsn:key})
 
                sender.append('mini.brd.vlt[%s] "%s"' % (num, removeQuotes(val)))   # static items for graph, could be duplicate

            break   # expecting no more than one block of voltages

    return (sender, json)


def getFanData(pOut_):

    sender = []
    json = []

    for block in pOut_:
        if 'Adapter: PCI adapter' in block:   # we dont need GPU fans
            continue
 
        regexp = None
        for r in FAN_REGEXPS:
            matchRe = re.search(r, block, re.I | re.M)
            if matchRe:
                regexp = r
                break

        if not regexp:
            continue  # nothing to match in current block

        fans = re.findall(regexp, block, re.I)
        for name, val in fans:
            clearName = sanitizeStr(name)
 
            # only create LLD when speed is not zero, BUT always send values including zero (prevents false triggering)
            valInt = int(val)
            sender.append('mini.fan[%s] "%s"' % (clearName, valInt))
            if valInt != 0:
                json.append({'{#FAN_NAME}':clearName})
 
    return (sender, json)


def getBoardTemps(pOut_):

    sender = []
    json = []

    for block in pOut_:
        if 'Adapter: PCI adapter' in block:   # we dont need GPU temps
            continue

        blockIdentRe = re.search(r'^.+', block)
        if blockIdentRe:
            blockIdent = blockIdentRe.group(0).strip()
        else:
            blockIdent = None
 
        temps = re.findall(BOARD_REGEXP, block, re.I | re.M)
        if temps:
            allTemps = []
            for name, val in temps:
                if isIgnoredMbSensor(blockIdent, name):
                    continue

                clearName = sanitizeStr(name)
                sender.append('mini.brd.temp[%s] "%s"' % (clearName, val))
                json.append({'{#BOARD_TEMP}':clearName})
                allTemps.append(int(val))

            sender.append('mini.brd.temp[MAX] "%s"' % (max(allTemps)))
            break  # unrelated blocks

    return (sender, json)


def getGpuData(pOut_):

    sender = []
    json = []

    gpuBlocks = -1
    allTemps = []
    for block in pOut_:
        regexp = None
        for r in GPU_REGEXPS:
            matchRe = re.search(r, block, re.I | re.M)
            if matchRe:
                regexp = r
                break

        if not regexp:
            continue  # nothing to match in current block

        gpuTempsRe = re.search(regexp, block, re.I | re.M)
        if gpuTempsRe:
            gpuid = gpuTempsRe.group(1)
            val   = gpuTempsRe.group(2)

            gpuBlocks += 1
            allTemps.append(int(val))

            json.append({'{#GPU}':gpuBlocks})
            sender.append('mini.gpu.info[gpu%s] "%s"' % (gpuBlocks, removeQuotes(gpuid)))

            json.append({'{#GPUTEMP}':gpuBlocks})
            sender.append('mini.gpu.temp[gpu%s] "%s"' % (gpuBlocks, val))

    if gpuBlocks != -1:
        if allTemps:
            error = None
            sender.append('mini.gpu.temp[MAX] "%s"' % (max(allTemps)))
        else:
            error = 'NOGPUTEMPS'   # unreachable
    else:
        error = 'NOGPUS'

    return (sender, json, error)


def getCpuData(pOut_):
    """Note: certain cores can pose as different blocks making them separate cpus in zabbix"""
    sender = []
    json = []

    cpuBlocks = -1   # first cpu will be '0'
    allTemps = []
    for block in pOut_:
        regexp = chooseCpuRegexp(block)
        if not regexp:
            continue  # nothing to match in current block

        coreTempsRe = re.findall(regexp, block, re.I | re.M)
        if coreTempsRe:
            cpuBlocks += 1

            json.append({'{#CPU}':cpuBlocks})
            sender.append('mini.cpu.info[cpu%s] "%s"' % (cpuBlocks, removeQuotes(block.splitlines()[0])))

            tempMax = re.search(r'_max:\s+(\d+)\.\d+', block, re.I)  # TjMax
            if tempMax:
                tjMax = tempMax.group(1)
            else:
                tjMax = FALLBACK_TJMAX

            sender.append('mini.cpu.info[cpu%s,TjMax] "%s"' % (cpuBlocks, tjMax))

            cpuTemps = []
            previousCore = None
            for num, val in coreTempsRe:
                if previousCore == num:
                    continue   # some cores have the same number - ignore them
                previousCore = num

                cpuTemps.append(int(val))
                allTemps.append(int(val))
                sender.append('mini.cpu.temp[cpu%s,core%s] "%s"' % (cpuBlocks, num, val))
                json.append({'{#CPUC}':cpuBlocks, '{#CORE}':num})

            sender.append('mini.cpu.temp[cpu%s,MAX] "%s"' % (cpuBlocks, max(cpuTemps)))

    if cpuBlocks != -1:
        if allTemps:
            error = None
            sender.append('mini.cpu.temp[MAX] "%s"' % (max(allTemps)))
        else:
            error = 'NOCPUTEMPS'
    else:
        error = 'NOCPUS'

    return (sender, json, error)


def chooseCpuRegexp(block_):

    result = None
    for regexp in CPU_REGEXPS:
        matchRe = re.search(regexp, block_, re.I | re.M)
        if matchRe:
            result = regexp
            break

    return result


def isIgnoredMbSensor(ident_, sensor_):

    result = False
    for ident, sensor in IGNORED_SENSORS:
        if (ident_  == ident and
            sensor_ == sensor):

            result = True
            break

    return result


def main(pOut_, pRunStatus_, host_):

    jsonData = []
    bareSenderData = []
    statusErrors = []

    if pOut_:
        pOut_ = pOut_.strip()
        allBlocks = pOut_.split('\n\n')
        allBlocks.sort()

        if GATHER_VOLTAGES:
            getVoltages_Out = getVoltages(allBlocks)
            bareSenderData.extend(getVoltages_Out[0])
            jsonData.extend(getVoltages_Out[1])

        if GATHER_FANS:
            getFanData_Out = getFanData(allBlocks)
            bareSenderData.extend(getFanData_Out[0])
            jsonData.extend(getFanData_Out[1])

        if GATHER_BOARD_TEMPS:
            getBoardTemps_Out = getBoardTemps(allBlocks)
            bareSenderData.extend(getBoardTemps_Out[0])
            jsonData.extend(getBoardTemps_Out[1])

        if GATHER_GPU_DATA:
            getGpuData_Out = getGpuData(allBlocks)
            gpuErrors = getGpuData_Out[2]
            bareSenderData.extend(getGpuData_Out[0])
            jsonData.extend(getGpuData_Out[1])
            if gpuErrors:
                statusErrors.append(gpuErrors)  # NOGPUS, NOGPUTEMPS

        if GATHER_CPU_DATA:
            getCpuData_Out = getCpuData(allBlocks)
            cpuErrors = getCpuData_Out[2]
            bareSenderData.extend(getCpuData_Out[0])
            jsonData.extend(getCpuData_Out[1])
            if cpuErrors:
                statusErrors.append(cpuErrors)  # NOCPUS, NOCPUTEMPS

    if statusErrors:
        errorsString = ', '.join(statusErrors).strip()
        bareSenderData.append('mini.cpu.info[ConfigStatus] "%s"' % errorsString)
    else:
        bareSenderData.append('mini.cpu.info[ConfigStatus] "%s"' % pRunStatus_)  # UNKNOWN_ERROR, NO_SENSORS, OS_NOCMD, OS_ERROR, UNKNOWN_EXC_ERROR, CONFIGURED

    # Add host ident to sender data
    senderData = []
    for i in bareSenderData:
        senderData.append(f'"{host_}" {i}')

    return (jsonData, senderData)


if __name__ == '__main__':

    fail_ifNot_Py3()

    (pRunStatus, pOut) = getOutput(BIN_PATH)

    host = sys.argv[2]
    (jsonData, senderData) = main(pOut, pRunStatus, host)

    link = r'https://github.com/nobody43/zabbix-mini-IPMI/issues'
    sendStatusKey = 'mini.cpu.info[SendStatus]'
    processData(senderData, jsonData, AGENT_CONF_PATH, SENDER_WRAPPER_PATH, SENDER_PATH, DELAY, host, link, sendStatusKey)

