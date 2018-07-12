#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

#binPath = r'OpenHardwareMonitorReport.exe'
binPath = r'C:\distr\OpenHardwareMonitorReport\OpenHardwareMonitorReport.exe'   # if OHMR isn't in PATH

# path to second send script
senderPyPath = r'C:\zabbix-agent\scripts\sender_wrapper.py'

# path to zabbix agent configuration file
agentConf = r'C:\zabbix_agentd.conf'

#senderPath = r'zabbix_sender'
senderPath = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'

timeout = '80'              # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                            # this setting MUST be lower than 'Update interval' in discovery rule

fallbackTjmax = '70'        # this value will be set to 'mini.cpu.info[cpu{#CPU},TjMax]' when it's not found on processor or in manualThresholds
fallbackVcoremax = '1.35'   # maximum allowed voltage for system processor, board-wide
vttMax = '1.1'              # processor-specific maximum VTT, board-wide

# Predefined sets of Vcore maximum voltages and TjMax. Corresponds to 'mini.brd.info[vcoreMax]' and 'mini.cpu.info[cpu{#CPU},TjMax]' items.
# All numeric values must be quoted. '%ANY%' will work only in board name field. 'None' will try to aquire values from output and 'fallbackTjmax'. 
# TjMax comparison will try to match cpu only. Vcore comparison will try to match board and cpu. Especially useful in case of incorrect multipliers.

manualThresholds = ( # Exact 'MainboardName' #    # Exact 'cpu{#CPU},TjMax' #                    # Vcore max voltage #    # TjMax #
                    ('M3N78-VM',                  'AMD Athlon 64 X2 Dual Core Processor 5200+',  '1.42',                  '72'),   # on board 'M3N78-VM' with cpu 'AMD Athlon 64 X2 Dual Core Processor 5200+' key 'mini.brd.info[vcoreMax]' will be set to '1.42'. 'mini.cpu.info[cpu{#CPU},TjMax]' will be set to '72' regardless of board name
                    ('P5KPL-AM IN/ROEM/SI',       'Intel Core 2 Duo E7500',                      '1.9',                   None),   # on board 'P5KPL-AM IN/ROEM/SI' with cpu 'Intel Core 2 Duo E7500' key 'mini.brd.info[vcoreMax]' will be set to '1.9'. 'mini.cpu.info[cpu{#CPU},TjMax]' will be queried from output and fallbackTjmax as last resort
                    ('%ANY%',                     'Intel Pentium 4 3.00GHz',                     '1.37',                  None),   # on any board with cpu 'Intel Pentium 4 3.00GHz' key 'mini.brd.info[vcoreMax]' will be set to '1.36' and 'mini.cpu.info[cpu{#CPU},TjMax]' will be set to fallbackTjmax (as there's no sensor on this cpu)
                   )

ignoreBoardTemp =  (
                    ('H110M-R',           'Temperature #6'),          # ignore 'Temperature #6' on board 'H110M-R' (readings from mars)
                  # ('EXAMPLE_BOARDNAME', 'EXAMPLE_TEMPERATURENAME'),
                  # ('Pull requests',     'are welcome'),
                   )

# Following settings brings (almost) no overhead. Use 'no' to disable unneeded data.
gatherBoardFans = 'yes'
gatherBoardTemp = 'yes'
gatherVoltages =  'yes'
gatherCpuData =   'yes'
gatherGpuData =   'yes'

## End of configuration ##

import sys
import subprocess
import re
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3)


def getOutput():
    p = None
    try:
        p = subprocess.check_output([binPath], universal_newlines=True)
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

    # Prevent empty results
    m0 = 'Status: Extracting driver failed'
    m1 = 'First Exception: OpenSCManager returned zero.'
    m2 = 'Second Exception: OpenSCManager returned zero.'
    if m0 in p or \
       m1 in p or \
       m2 in p:
        print('OHMR failed. Try again.')
        sys.exit(1)

    return error, p


def getBoardInfo():
    sender = []

    OHMRver = re.search(r'^Version:\s+(.+)$', pOut, re.I | re.M)
    if OHMRver:
        sender.append(host + ' mini.info[OHMRver] "' + OHMRver.group(1).strip() + '"')

    SMBIOS = re.search(r'^SMBIOS\s+Version:\s+(.+)$', pOut, re.I | re.M)
    if SMBIOS:
        sender.append(host + ' mini.brd.info[SMBIOSversion] "' + SMBIOS.group(1).strip() + '"')

    BIOSvendor = re.search(r'^BIOS\s+Vendor:\s+(.+)$', pOut, re.I | re.M)
    if BIOSvendor:
        sender.append(host + ' mini.brd.info[BIOSvendor] "' + BIOSvendor.group(1).strip() + '"')

    BIOSver = re.search(r'^BIOS\s+Version:\s+(.+)$', pOut, re.I | re.M)
    if BIOSver:
        sender.append(host + ' mini.brd.info[BIOSversion] "' + BIOSver.group(1).strip() + '"')

    boardManuf = re.search(r'^Mainboard\s+Manufacturer:\s+(.+)$', pOut, re.I | re.M)
    if boardManuf:
        sender.append(host + ' mini.brd.info[MainboardManufacturer] "' + boardManuf.group(1).strip() + '"')

    boardNameRe = re.search(r'^Mainboard\s+Name:\s+(.+)$', pOut, re.I | re.M)
    if boardNameRe:
        sender.append(host + ' mini.brd.info[MainboardName] "' + boardNameRe.group(1).strip() + '"')

    boardVersion = re.search(r'^Mainboard\s+Version:\s+(.+)$', pOut, re.I | re.M)
    if boardVersion:
        sender.append(host + ' mini.brd.info[MainboardVersion] "' + boardVersion.group(1).strip() + '"')

    return sender, boardNameRe.group(1).strip()


def getVoltages():
    '''Tries to get motherboard voltages.'''
    sender = []
    json = []

    voltages = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+\.\d+|\d+)\s+.+\(\/lpc\/[\w-]+\/voltage\/(\d+)\)', pOut, re.I)   # slightly loose

    for i in voltages:

        if re.search('VCore', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[cpuVcore] "' + i[1] + '"')
            json.append({'{#VCORE}':'cpuVcore'})   # hardcoded because of zabbix stubbornness

        elif re.match('VBAT', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[VBat] "' + i[1] + '"')
            json.append({'{#VBAT}':'VBat'})

        elif re.match('3VSB', i[0], re.I) or re.match('VSB3V', i[0], re.I) or re.match(r'Standby \+3\.3V', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[VSB3V] "' + i[1] + '"')
            json.append({'{#VSB3V}':'VSB3V'})

        elif re.match('3VCC', i[0], re.I) or re.match('VCC3V', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[VCC3V] "' + i[1] + '"')
            json.append({'{#VCC3V}':'VCC3V'})

        elif re.match('AVCC', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[AVCC] "' + i[1] + '"')
            json.append({'{#VAVCC}':'AVCC'})

        elif re.match('VTT', i[0], re.I):
            sender.append(host + ' mini.brd.vlt[VTT] "' + i[1] + '"')
            json.append({'{#VTT}':'VTT'})

            sender.append(host + ' mini.brd.info[vttMax] "' + vttMax + '"')

        sender.append(host + ' mini.brd.vlt[' + i[2] + '] "' + i[1] + '"')   # static items for graph, could be duplicate

    return sender, json


def getBoardFans():
    sender = []
    json = []

    fans = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+).+\(\/lpc\/[\w-]+\/fan\/(\d+)\)', pOut, re.I)
    for i in fans:
        k = i[0].strip()

        # only create LLD when speed is not zero, BUT always send zero values (hides phantom fans)
        sender.append(host + ' mini.brd.fan[' + i[2] + ',rpm] "' + i[1] + '"')
        if i[1] != '0':
            json.append({'{#BRDFANNAME}':k, '{#BRDFANNUM}':i[2]})

    return sender, json


def getBoardTemp(currentBoard):
    sender = []
    json = []

    temps = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+).+\(\/lpc\/[\w-]+\/temperature\/(\d+)\)', pOut, re.I)

    allTemps = []
    for i in temps:
        temperatureName = i[0].strip()

        ignoredSensor = False
        if currentBoard:
            for boardReference, ignoredTemp in ignoreBoardTemp:
                if boardReference == currentBoard and ignoredTemp == temperatureName:
                    ignoredSensor = True

        if ignoredSensor:
            continue   # ignore iterated sensor if its found in configuration

        allTemps.append(int(i[1]))

        sender.append(host + ' mini.brd.temp[' + i[2] + '] "' + i[1] + '"')
        json.append({'{#BRDTEMPNAME}':temperatureName, '{#BRDTEMPNUM}':i[2]})

    if allTemps:
        sender.append(host + ' mini.brd.temp[MAX] "' + str(max(allTemps)) + '"')

    return sender, json


def getGpuData():
    sender = []
    json = []

    # determine available GPUs
    gpus = re.findall(r'\+\-\s+(.+)\s+\(\/[\w-]+gpu\/(\d+)\)', pOut, re.I)
    gpus = set(gpus)   # remove duplicates

    allTemps = []
    for i in gpus:
        errors = []
        sender.append(host + ' mini.gpu.info[gpu' + i[1] + ',ID] "' + i[0].strip() + '"')
        json.append({'{#GPU}':i[1]})

        temp = re.search(r':\s+(\d+).+\(\/[\w-]+gpu\/' + i[1] + '\/temperature\/0\)', pOut, re.I)
        if temp:
            json.append({'{#GPUTEMP}':i[1]})
            allTemps.append(int(temp.group(1)))
            sender.append(host + ' mini.gpu.temp[gpu' + i[1] + '] "' + temp.group(1) + '"')
        else:
            errors.append('NO_TEMP')

        fanspeed = re.search(r':\s+(\d+).+\(\/[\w-]+gpu\/' + i[1] + '\/fan\/0\)', pOut, re.I)
        if fanspeed:
            sender.append(host + ' mini.gpu.fan[gpu' + i[1] + ',rpm] "' + fanspeed.group(1) + '"')
            if fanspeed.group(1) != '0':
                json.append({'{#GPUFAN}':i[1]})
        else:
            errors.append('NO_FAN')

        memory = re.findall(r'\+\-\s+(GPU\s+Memory\s+Free|GPU\s+Memory\s+Used|GPU\s+Memory\s+Total)\s+:\s+(\d+).+\(\/[\w-]+gpu\/' + i[1] + '\/smalldata\/\d+\)', pOut, re.I)
        if memory:
            json.append({'{#GPUMEM}':i[1]})
            for m in memory:   # more controllable
                if 'Free' in m[0]:
                    sender.append(host + ' mini.gpu.memory[gpu' + i[1] + ',free] "' + m[1] + '"')
                elif 'Used' in m[0]:
                    sender.append(host + ' mini.gpu.memory[gpu' + i[1] + ',used] "' + m[1] + '"')
                elif 'Total' in m[0]:
                    sender.append(host + ' mini.gpu.memory[gpu' + i[1] + ',total] "' + m[1] + '"')

        if errors:
            for e in errors:
                sender.append(host + ' mini.gpu.info[gpu' + i[1] + ',GPUstatus] "' + e + '"')   # NO_TEMP, NO_FAN
        else:
            sender.append(host + ' mini.gpu.info[gpu' + i[1] + ',GPUstatus] "PROCESSED"')

    if gpus:
        if allTemps:
            error = None
            sender.append(host + ' mini.gpu.temp[MAX] "' + str(max(allTemps)) + '"')
        else:
            error = 'NOGPUTEMPS'
    else:
        error = 'NOGPUS'

    return sender, json, error


def getTjmaxAndVcoremax(currentBoard, currentCpuID, currentCpuName):
    gotTjmax = False
    gotVcoremax = False
    for board, cpu, vcoremax, tjmax in manualThresholds:
        if board and cpu:                   # if values are not empty
            if board == currentBoard or \
               board == '%ANY%':            # board was found in threshholds

                # Board and CPU comparison
                if cpu == currentCpuName:    # cpu was found in threshholds
                    if vcoremax:
                        resultVcoremax = vcoremax
                        gotVcoremax = True

        # CPU-only comparison
        if cpu:
            if cpu == currentCpuName:
                if tjmax:
                    resultTjmax = tjmax
                    gotTjmax = True

    if not gotTjmax:
        tjMaxRe = re.search(r'\(\/[\w-]+cpu\/' + currentCpuID + '\/temperature\/\d+\)\s+\|\s+\|\s+\+\-\s+TjMax\s+\[\S+\]\s+:\s+(\d+)', pOut, re.I | re.M)
        if tjMaxRe:
            resultTjmax = tjMaxRe.group(1)
        else:
            resultTjmax = fallbackTjmax

    if not gotVcoremax:
        resultVcoremax = fallbackVcoremax

    return resultTjmax, resultVcoremax


def getCpuData(currentBoard):
    sender = []
    json = []

    # determine available CPUs
    CPUs = re.findall(r'\+\-\s+(.+)\s+\(\/[\w-]+cpu\/(\d+)\)', pOut, re.I)
    CPUs = set(CPUs)   # remove duplicates

    allTemps = []
    for cpu in CPUs:
        # Processor model
        sender.append(host + ' mini.cpu.info[cpu' + cpu[1] + ',ID] "' + cpu[0].strip() + '"')
        json.append({'{#CPU}':cpu[1]})

        getTjmaxAndVcoremax_Out = getTjmaxAndVcoremax(currentBoard, cpu[1], cpu[0])
        sender.append('%s mini.cpu.info[cpu%s,TjMax] "%s"' % (host, cpu[1], getTjmaxAndVcoremax_Out[0]))
        sender.append('%s mini.brd.info[vcoreMax] "%s"' % (host, getTjmaxAndVcoremax_Out[1]))   # same results for multiple cpus

        # All core temperatures for given CPU
        coreTempsRe = re.findall(r'Core.+:\s+(\d+).+\(\/[\w-]+cpu\/' + cpu[1] + '\/temperature\/(\d+)\)', pOut, re.I)
        if coreTempsRe:
            sender.append(host + ' mini.cpu.info[cpu' + cpu[1] + ',CPUstatus] "PROCESSED"')
            cpuTemps = []
            for core in coreTempsRe:
                cpuTemps.append(int(core[0]))
                allTemps.append(int(core[0]))
                sender.append(host + ' mini.cpu.temp[cpu' + cpu[1] + ',core' + core[1] + '] "' + core[0] + '"')
                json.append({'{#CPUC}':cpu[1], '{#CORE}':core[1]})

            sender.append(host + ' mini.cpu.temp[cpu' + cpu[1] + ',MAX] "' + str(max(cpuTemps)) + '"')
        else:
            sender.append(host + ' mini.cpu.info[cpu' + cpu[1] + ',CPUstatus] "NO_TEMP"')

    if CPUs:
        if allTemps:
            error = None
            sender.append(host + ' mini.cpu.temp[MAX] "' + str(max(allTemps)) + '"')
        else:
            error = 'NOCPUTEMPS'
    else:
        error = 'NOCPUS'

    return sender, json, error


if __name__ == '__main__':
    fail_ifNot_Py3()

    host = '"' + sys.argv[2] + '"'
    senderData = []
    jsonData = []

    getOutput_Out = getOutput()

    statusC = None
    if getOutput_Out[1]:   # process output
        pOut = getOutput_Out[1]

        getBoardInfo_Out = getBoardInfo()
        senderData.extend(getBoardInfo_Out[0])
        currentBoard = getBoardInfo_Out[1]

        if gatherBoardTemp == 'yes':
            getBoardTemp_Out = getBoardTemp(currentBoard)
            senderData.extend(getBoardTemp_Out[0])
            jsonData.extend(getBoardTemp_Out[1])

        if gatherVoltages == 'yes':
            getVoltages_Out = getVoltages()
            senderData.extend(getVoltages_Out[0])
            jsonData.extend(getVoltages_Out[1])

        if gatherBoardFans == 'yes':
            getBoardFans_Out = getBoardFans()
            senderData.extend(getBoardFans_Out[0])
            jsonData.extend(getBoardFans_Out[1])

        if gatherGpuData == 'yes':
            getGpuData_Out = getGpuData()
            senderData.extend(getGpuData_Out[0])
            jsonData.extend(getGpuData_Out[1])
            if getGpuData_Out[2]:
                statusC = 'gpu_err'
                # mini.cpu.info[ConfigStatus] is used to track configuration states including cpu and gpu:
                senderData.append(host + ' mini.cpu.info[ConfigStatus] "' + getGpuData_Out[2] + '"')   # NOGPUS, NOGPUTEMPS

        if gatherCpuData == 'yes':
            getCpuData_Out = getCpuData(currentBoard)
            senderData.extend(getCpuData_Out[0])
            jsonData.extend(getCpuData_Out[1])
            if getCpuData_Out[2]:
                statusC = 'cpu_err'
                senderData.append(host + ' mini.cpu.info[ConfigStatus] "' + getCpuData_Out[2] + '"')   # NOCPUS, NOCPUTEMPS (comes after gpu call and can supersede its errors on trigger)

    if not statusC:
        senderData.append(host + ' mini.cpu.info[ConfigStatus] "' + getOutput_Out[0] + '"')   # OS_NOCMD, OS_ERROR, UNKNOWN_EXC_ERROR, CONFIGURED

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    processData(senderData, jsonData, agentConf, senderPyPath, senderPath, timeout, host, link)

