#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

#BIN_PATH = r'OpenHardwareMonitorReport.exe'
BIN_PATH = r'C:\distr\OpenHardwareMonitorReport\OpenHardwareMonitorReport.exe'   # if OHMR isn't in PATH

# path to send script
SENDER_WRAPPER_PATH = r'C:\zabbix-agent\scripts\sender_wrapper.py'

# path to zabbix agent configuration file
AGENT_CONF_PATH = r'C:\zabbix_agentd.conf'

#SENDER_PATH = r'zabbix_sender'
SENDER_PATH = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'

PARAMS = 'reporttoconsole --IgnoreMonitorHDD --IgnoreMonitorRAM'
# Possible params:
# --IgnoreMonitorCPU
# --IgnoreMonitorFanController
# --IgnoreMonitorGPU
# --IgnoreMonitorHDD
# --IgnoreMonitorMainboard
# --IgnoreMonitorRAM

SKIP_PARAMS_ON_WINXP = True    # True or False

# Advanced configuration

# Supply absent Tjmax
MANUAL_TJMAXES = (
    ('AMD Athlon 64 X2 Dual Core Processor 5200+',  '72'),
)

# Ignore specific temperature by name on specific board
IGNORED_SENSORS = (
    ('H110M-R',           'Temperature #6'),          # ignore 'Temperature #6' on board 'H110M-R'
#   ('EXAMPLE_BOARDNAME', 'EXAMPLE_TEMPERATURENAME'),
#   ('Pull requests',     'are welcome'),
)

# These CPUs will produce NO_SENSOR trigger instead of NO_TEMP
CPUS_WITHOUT_SENSOR = (
    'Intel Pentium 4 3.00GHz',
)

BOARD_REGEXPS_AND_KEYS = (
    ('^SMBIOS\s+Version:\s+(.+)$',          'mini.brd.info[SMBIOSversion]'),
    ('^BIOS\s+Vendor:\s+(.+)$',             'mini.brd.info[BIOSvendor]'),
    ('^BIOS\s+Version:\s+(.+)$',            'mini.brd.info[BIOSversion]'),
    ('^Mainboard\s+Manufacturer:\s+(.+)$',  'mini.brd.info[MainboardManufacturer]'),
    ('^Mainboard\s+Name:\s+(.+)$',          'mini.brd.info[MainboardName]'),
    ('^Mainboard\s+Version:\s+(.+)$',       'mini.brd.info[MainboardVersion]'),
)

VOLTAGE_REGEXPS_KEYS_AND_JSONS = (
    ('^VCore$',                             'cpuVcore', '{#VCORE}'),
    ('^VBAT$',                              'VBat',     '{#VBAT}'),
    ('(^3VSB$|^VSB3V$|^Standby \+3\.3V$)',  'VSB3V',    '{#VSB3V}'),
    ('(^3VCC$|^VCC3V$)',                    'VCC3V',    '{#VCC3V}'),
    ('^AVCC$',                              'AVCC',     '{#VAVCC}'),
    ('^VTT$',                               'VTT',      '{#VTT}'),
)

TIMEOUT = '80'              # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
                            # this setting MUST be lower than 'Update interval' in discovery rule

## End of configuration ##

import sys
import subprocess
import re
import platform
from sender_wrapper import (readConfig, processData, fail_ifNot_Py3, removeQuotes)

HOST = sys.argv[2]


def chooseCmd(binPath_, params_):

    cmd = '%s %s' % (binPath_, params_)

    if not SKIP_PARAMS_ON_WINXP:
        if platform.release() == "XP":
            cmd = binPath_
    
    return cmd
    

def getOutput(cmd_):
    p = None
    try:
        p = subprocess.check_output(cmd_, universal_newlines=True)
    except OSError as e:
        if e.args[0] == 2:
            status = 'OS_NOCMD'
        else:
            status = 'OS_ERROR'
            if sys.argv[1] == 'getverb':
                raise
    except Exception as e:
        status = 'UNKNOWN_EXC_ERROR'

        if sys.argv[1] == 'getverb':
            raise

        try:
            p = e.output
        except:
            pass
    else:
        status = 'CONFIGURED'

    # Prevent empty results
    if p:
        m0 = 'Status: Extracting driver failed'
        m1 = 'First Exception: OpenSCManager returned zero.'
        m2 = 'Second Exception: OpenSCManager returned zero.'
        if    (m0 in p or
               m1 in p or
               m2 in p):
               
            print('OHMR failed. Try again.')
            sys.exit(1)

    return status, p


def getOHMRversion(pOut_):

    OHMRver = re.search(r'^Version:\s+(.+)$', pOut_, re.I | re.M)
    if OHMRver:
        version = OHMRver.group(1).strip()
    else:
        version = None
        
    sender = ['"%s" mini.info[OHMRversion] "%s"' % (HOST, removeQuotes(version))]
        
    return sender
    
    
def getBoardInfo(pOut_):

    sender = []

    for regexp, key in BOARD_REGEXPS_AND_KEYS:
        reMatch = re.search(regexp, pOut_, re.I | re.M)
        if reMatch:
            sender.append('"%s" %s "%s"' % (HOST, key, removeQuotes(reMatch.group(1).strip())))

    return sender


def getBoardName(pOut_):

    boardRe = re.search(r'^Mainboard\s+Name:\s+(.+)$', pOut_, re.I | re.M)
    if boardRe:
        board = boardRe.group(1).strip()
    else:
        board = None

    return board
    
    
def getTjmax(pOut_, cpuID_, cpuName_):
    
    tjMaxRe = re.search(r'\(\/[\w-]+cpu\/%s\/temperature\/\d+\)\s+\|\s+\|\s+\+\-\s+TjMax\s+\[\S+\]\s+:\s+(\d+)' % cpuID_, pOut_, re.I | re.M)
    if tjMaxRe:
        tjmax = tjMaxRe.group(1)
    else:
        tjmax = None
        for name, val in MANUAL_TJMAXES:
            if name == cpuName_:
                tjmax = val
                break

    return tjmax
    
    
def isCpuWithoutSensor(cpuname_):

    if cpuname_ in CPUS_WITHOUT_SENSOR:
        result = True
    else:
        result = False

    return result
    
    
def isCpuSensorPresent(pOut_):

    coreTempsRe = re.search(r'Core.+:\s+\d+.+\(\/[\w-]+cpu\/\d+\/temperature\/\d+\)', pOut_, re.I)
    if coreTempsRe:
        result = True
    else:
        result = False

    return result
    
    
def isParamIgnored(param_):

    if param_ in PARAMS:
        result = True
    else:
        result = False
        
    return result
    
    
def getCpusData(pOut_):

    sender = []
    json = []

    # determine available CPUs
    cpusRe = re.findall(r'\+\-\s+(.+)\s+\(\/[\w-]+cpu\/(\d+)\)', pOut_, re.I)
    cpus = set(cpusRe)
    #print(cpusRe)

    allTemps = []
    for name, id in cpus:
        # Processor model
        sender.append('"%s" mini.cpu.info[cpu%s,ID] "%s"' % (HOST, id, removeQuotes(name.strip())))
        json.append({'{#CPU}':id})

        gotTjmax = getTjmax(pOut_, id, name)
        if gotTjmax:
            sender.append('"%s" mini.cpu.info[cpu%s,TjMax] "%s"' % (HOST, id, gotTjmax))

        # All core temperatures for given CPU
        coreTempsRe = re.findall(r'Core.+:\s+(\d+).+\(\/[\w-]+cpu\/%s\/temperature\/(\d+)\)' % id, pOut_, re.I)
        if coreTempsRe:
            sender.append('"%s" mini.cpu.info[cpu%s,CPUstatus] "PROCESSED"' % (HOST, id))
            cpuTemps = []
            for coretemp, coreid in coreTempsRe:
                cpuTemps.append(int(coretemp))
                allTemps.append(int(coretemp))
                sender.append('"%s" mini.cpu.temp[cpu%s,core%s] "%s"' % (HOST, id, coreid, coretemp))
                json.append({'{#CPUC}':id, '{#CORE}':coreid})

            sender.append('"%s" mini.cpu.temp[cpu%s,MAX] "%s"' % (HOST, id, str(max(cpuTemps))))

        elif isCpuWithoutSensor(name):
            sender.append('"%s" mini.cpu.info[cpu%s,CPUstatus] "NO_SENSOR"' % (HOST, id))
        else:
            sender.append('"%s" mini.cpu.info[cpu%s,CPUstatus] "NO_TEMP"'   % (HOST, id))

    if cpus:
        if allTemps:
            error = None
            sender.append('"%s" mini.cpu.temp[MAX] "%s"' % (HOST , str(max(allTemps))))
        else:
            error = 'NOCPUTEMPS'
    else:
        error = 'NOCPUS'

    return sender, json, error
    
    
def getVoltages(pOut_):

    sender = []
    json = []

    voltagesRe = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+\.\d+|\d+)\s+.+\(\/lpc\/[\w-]+\/voltage\/(\d+)\)', pOut_, re.I)
    for name, val, id in voltagesRe:
        name = name.strip()

        for regexp, key, jsn in VOLTAGE_REGEXPS_KEYS_AND_JSONS:
            if re.search(regexp, name, re.I):
                sender.append('"%s" mini.brd.vlt[%s] "%s"' % (HOST, key, removeQuotes(val)))
                json.append({jsn:key})

        sender.append('"%s" mini.brd.vlt[%s] "%s"' % (HOST, id, removeQuotes(val)))   # static items for graph, could be duplicate

    return sender, json


def getBoardFans(pOut_):

    sender = []
    json = []

    fansRe = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+).+\(\/lpc\/[\w-]+\/fan\/(\d+)\)', pOut_, re.I)
    for name, val, num in fansRe:
        name = name.strip()

        # Only create LLD when speed is not zero, BUT always send zero values (hides phantom fans)
        sender.append('"%s" mini.brd.fan[%s,rpm] "%s"' % (HOST, num, val))
        if val != '0':
            json.append({'{#BRDFANNAME}':name, '{#BRDFANNUM}':num})

    return sender, json


def getBoardTemps(pOut_):
    sender = []
    json = []
    
    board = getBoardName(pOut_)

    tempsRe = re.findall(r'\+\-\s+(.+)\s+:\s+(\d+).+\(\/lpc\/[\w-]+\/temperature\/(\d+)\)', pOut_, re.I)
    #print(tempsRe)

    allTemps = []
    for name, val, id in tempsRe:
        name = name.strip()
        
        if  (isCpuSensorPresent(pOut_) and
             re.match('^CPU Core$|^CPU$', name)):
            
            continue

        ignoredSensor = False
        if board:
            for boardReference, ignoredTempName in IGNORED_SENSORS:
                if      (boardReference == board and
                         ignoredTempName    == name):
                    ignoredSensor = True

        if ignoredSensor:
            continue

        allTemps.append(int(val))

        sender.append('"%s" mini.brd.temp[%s] "%s"' % (HOST, id, val))
        json.append({'{#BRDTEMPNAME}':name, '{#BRDTEMPNUM}':id})

    if allTemps:
        sender.append('"%s" mini.brd.temp[MAX] "%s"' % (HOST, str(max(allTemps))))

    return sender, json


def getGpusData(pOut_):
    sender = []
    json = []

    # Determine available GPUs
    gpusRe = re.findall(r'\+\-\s+(.+)\s+\(\/[\w-]+gpu\/(\d+)\)', pOut_, re.I)
    gpus = set(gpusRe)   # remove duplicates

    allTemps = []
    for name, num in gpus:
        errors = []
        sender.append('"%s" mini.gpu.info[gpu%s,ID] "%s"' % (HOST, num, name.strip()))
        json.append({'{#GPU}':num})
        
        temp = re.search(r':\s+(\d+).+\(\/[\w-]+gpu\/%s\/temperature\/0\)' % num, pOut_, re.I)
        if temp:
            json.append({'{#GPUTEMP}':num})
            allTemps.append(int(temp.group(1)))
            sender.append('"%s" mini.gpu.temp[gpu%s] "%s"' % (HOST, num, temp.group(1)))
        else:
            errors.append('NO_TEMP')

        fanspeed = re.search(r':\s+(\d+).+\(\/[\w-]+gpu\/%s\/fan\/0\)' % num, pOut_, re.I)
        if fanspeed:
            sender.append('"%s" mini.gpu.fan[gpu%s,rpm] "%s"' % (HOST, num, fanspeed.group(1)))
            if fanspeed.group(1) != '0':
                json.append({'{#GPUFAN}':num})
        else:
            errors.append('NO_FAN')

        memory = re.findall(r'\+\-\s+(GPU\s+Memory\s+Free|GPU\s+Memory\s+Used|GPU\s+Memory\s+Total)\s+:\s+(\d+).+\(\/[\w-]+gpu\/%s\/smalldata\/\d+\)' % num, pOut_, re.I)
        if memory:
            json.append({'{#GPUMEM}':num})
            for memname, memval in memory:   # more controllable
                if 'Free' in memname:
                    sender.append('"%s" mini.gpu.memory[gpu%s,free] "%s"'   % (HOST, num, memval))
                elif 'Used' in memname:
                    sender.append('"%s" mini.gpu.memory[gpu%s,used] "%s"'   % (HOST, num, memval))
                elif 'Total' in memname:
                    sender.append('"%s" mini.gpu.memory[gpu%s,total] "%s"'  % (HOST, num, memval))

        if errors:
            for e in errors:
                sender.append('"%s" mini.gpu.info[gpu%s,GPUstatus] "%s"'    % (HOST, num, e))   # NO_TEMP, NO_FAN
        else:
            sender.append('"%s" mini.gpu.info[gpu%s,GPUstatus] "PROCESSED"' % (HOST, num))

    if gpus:
        if allTemps:
            statusError = None
            sender.append('"%s" mini.gpu.temp[MAX] "%s"' % (HOST, str(max(allTemps))))
        else:
            statusError = 'NOGPUTEMPS'
    else:
        statusError = 'NOGPUS'

    return sender, json, statusError


if __name__ == '__main__':

    fail_ifNot_Py3()

    senderData = []
    jsonData = []
    statusErrors = []

    cmd = chooseCmd(BIN_PATH, PARAMS)
    
    p_Output = getOutput(cmd)
    pRunStatus = p_Output[0]
    pOut = p_Output[1]
    
    if pOut:
        senderData.extend(getOHMRversion(pOut))
        
        senderData.extend(getBoardInfo(pOut))
        
        if not isParamIgnored('--IgnoreMonitorCPU'):
            cpuData_Out = getCpusData(pOut)
            if cpuData_Out:
                cpuSender = cpuData_Out[0]
                cpuJson =   cpuData_Out[1]
                cpuError =  cpuData_Out[2]
            
                senderData.extend(cpuSender)
                jsonData.extend(cpuJson)
                
                if cpuError:
                    statusErrors.append(cpuError)

        if not isParamIgnored('--IgnoreMonitorMainboard'):
            boardTemps_Out = getBoardTemps(pOut)
            if boardTemps_Out:
                boardSender = boardTemps_Out[0]
                boardJson =   boardTemps_Out[1]
                
                senderData.extend(boardSender)
                jsonData.extend(boardJson)
            
            voltages_Out = getVoltages(pOut)
            if voltages_Out:
                voltagesSender = voltages_Out[0]
                voltagesJson = voltages_Out[1]
                
                senderData.extend(voltagesSender)
                jsonData.extend(voltagesJson)
        
        if not isParamIgnored('--IgnoreMonitorFanController'):
            boardFans_Out = getBoardFans(pOut)
            if boardFans_Out:
                senderData.extend(boardFans_Out[0])
                jsonData.extend(boardFans_Out[1])
            
        if not isParamIgnored('--IgnoreMonitorGPU'):
            gpuData_Out = getGpusData(pOut)
            if gpuData_Out:
                gpuSender = gpuData_Out[0]
                gpuJson =   gpuData_Out[1]
                gpuError =  gpuData_Out[2]
                
                senderData.extend(gpuSender)
                jsonData.extend(gpuJson)
                
                if gpuError:
                    statusErrors.append(gpuError)
            
    if statusErrors:
        errorsString = ', '.join(statusErrors).strip()
        senderData.append('"%s" mini.cpu.info[ConfigStatus] "%s"' % (HOST, errorsString))
    elif pRunStatus:
        senderData.append('"%s" mini.cpu.info[ConfigStatus] "%s"' % (HOST, pRunStatus))
        
    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    sendStatusKey = 'mini.cpu.info[SendStatus]'
    processData(senderData, jsonData, AGENT_CONF_PATH, SENDER_WRAPPER_PATH, SENDER_PATH, TIMEOUT, HOST, link, sendStatusKey)

