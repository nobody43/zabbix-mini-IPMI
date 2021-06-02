#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-mini-IPMI ##

# Only one out of three system-specific setting is used, PATH considered.
binPath_LINUX      = r'sudo smartctl'
binPath_WIN        = r'C:\Program Files\smartmontools\bin\smartctl.exe'
binPath_OTHER      = r'sudo /usr/local/sbin/smartctl'

# path to zabbix agent configuration file
agentConf_LINUX    = r'/etc/zabbix/zabbix_agentd.conf'
agentConf_WIN      = r'C:\zabbix_agentd.conf'
agentConf_OTHER    = r'/usr/local/etc/zabbix3/zabbix_agentd.conf'

senderPath_LINUX   = r'zabbix_sender'
senderPath_WIN     = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'
senderPath_OTHER   = r'/usr/local/bin/zabbix_sender'

# path to second send script
senderPyPath_LINUX = r'/etc/zabbix/scripts/sender_wrapper.py'
senderPyPath_WIN   = r'C:\zabbix-agent\scripts\sender_wrapper.py'
senderPyPath_OTHER = r'/usr/local/etc/zabbix/scripts/sender_wrapper.py'


## Advanced configuration ##
# 'True' or 'False'
isCheckNVMe = False       # Additional overhead. Should be disabled if smartmontools is >= 7 or NVMe is absent.

isIgnoreDuplicates = True

# type, min, max, critical
thresholds = (
    ('hdd', 25, 45, 60),
)

isHeavyDebug = False

perDiskTimeout = 3   # Single disk query can not exceed this value. Python33 or above required.

timeout = '80'   # How long the script must wait between LLD and sending, increase if data received late (does not affect windows).
                 # This setting MUST be lower than 'Update interval' in discovery rule.

# Manually provide disk list or RAID configuration if needed.
diskListManual = []
# like this:
#diskListManual = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

# These models will not produce 'NOTEMP' warning. Pull requests are welcome.
noTemperatureSensorModels = (
    'INTEL SSDSC2CW060A3',
    'AXXROMBSASMR',
    'PLEXTOR PX-256M6Pro',
)

# re.IGNORECASE | re.MULTILINE
modelPatterns = (
    '^Device Model:\s+(.+)$',
    '^Device:\s+(.+)$',
    '^Product:\s+(.+)$',
    '^Model Number:\s+(.+)$',
)

# First match returned right away; re.IGNORECASE | re.MULTILINE
temperaturePatterns = (
    '^(?:\s+)?\d+\s+Temperature_Celsius\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)',
    '^(?:\s+)?\d+\s+Temperature_Internal\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)',
    '^(?:\s+)?\d+\s+Temperature_Case\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)',
    '^(?:\s+)?Current\s+Drive\s+Temperature:\s+(\d+)\s+',
    '^(?:\s+)?Temperature:\s+(\d+)\s+C',
    '^(?:\s+)?\d+\s+Airflow_Temperature_Cel\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)',
)

## End of configuration ##


import sys
import subprocess
import re
import shlex
from sender_wrapper import (fail_ifNot_Py3, sanitizeStr, clearDiskTypeStr, processData)


def scanDisks(mode):
    '''Determines available disks. Can be skipped.'''
    if mode == 'NOTYPE':
        cmd = binPath + ['--scan']
    elif mode == 'NVME':
        cmd = binPath + ['--scan', '-d', 'nvme']
    else:
        print('Invalid type %s. Terminating.' % mode)
        sys.exit(1)

    try:
        p = subprocess.check_output(cmd, universal_newlines=True)
        error = ''
    except OSError as e:
        p = ''

        if e.args[0] == 2:
            error = 'SCAN_OS_NOCMD_%s' % mode
        else:
            error = 'SCAN_OS_ERROR_%s' % mode

    except Exception as e:
        try:
            p = e.output
        except:
            p = ''

        error = 'SCAN_UNKNOWN_ERROR_%s' % mode
        if sys.argv[1] == 'getverb':
            raise

    # TESTING
    #if mode == 'NVME': p = '''/dev/nvme0 -d nvme # /dev/nvme0, NVMe device\n/dev/bus/0 -d megaraid,4 # /dev/bus/0 [megaraid_disk_04], SCSI device'''
            
    # Determine full device names and types
    disks = re.findall(r'^(/dev/[^#]+)', p, re.M)

    return error, disks


def moveCsmiToBegining(disks):
    csmis = []
    others = []
    
    for i in disks:
        if re.search(r'\/csmi\d+\,\d+', i, re.I):
            csmis.append(i)
        else:
            others.append(i)

    result = csmis + others

    return result


def listDisks():
    errors = []

    if not diskListManual:
        scanDisks_Out = scanDisks('NOTYPE')
        errors.append(scanDisks_Out[0])   # SCAN_OS_NOCMD_*, SCAN_OS_ERROR_*, SCAN_UNKNOWN_ERROR_*

        disks = scanDisks_Out[1]

        if isCheckNVMe:
            scanDisksNVMe_Out = scanDisks('NVME')
            errors.append(scanDisksNVMe_Out[0])

            disks.extend(scanDisksNVMe_Out[1])
        else:
            errors.append('')

    else:
        disks = diskListManual

    # Remove duplicates preserving order
    diskResult = []
    for i in disks:
        if i not in diskResult:
            diskResult.append(i)

    diskResult = moveCsmiToBegining(diskResult)

    return errors, diskResult


def findErrorsAndOuts(cD):
    err = None
    p = ''

    try:
        cmd = binPath + ['-A', '-i', '-n', 'standby'] + shlex.split(cD)

        if      (sys.version_info.major == 3 and
                 sys.version_info.minor <= 2):
                 
            p = subprocess.check_output(cmd, universal_newlines=True)
            
            err = 'OLD_PYTHON32_OR_LESS'
        else:
            p = subprocess.check_output(cmd, universal_newlines=True, timeout=perDiskTimeout)

    except OSError as e:
        if e.args[0] == 2:
            err = 'D_OS_NOCMD'
        else:
            err = 'D_OS_ERROR'
            if sys.argv[1] == 'getverb': raise

    except subprocess.CalledProcessError as e:
        p = e.output

        if   'Device is in STANDBY (OS)' in p:
            err = 'STANDBY_OS'
        elif 'Device is in STANDBY' in p:
            err = 'STANDBY'
        elif 'Device is in SLEEP' in p:
            err = 'SLEEP'
        elif 'Unknown USB bridge' in p:
            err = 'UNK_USB_BRIDGE'
        elif r"Packet Interface Devices [this device: CD/DVD] don't support ATA SMART" in p:
            err = 'CD_DVD_DRIVE'
            
        elif    (sys.version_info.major == 3 and
                 sys.version_info.minor <= 1):

            err = 'UNK_OLD_PYTHON31_OR_LESS'

        elif e.args:
            err = 'ERR_CODE_%s' % str(e.args[0])
        else:
            err = 'UNKNOWN_RESPONSE'

    except subprocess.TimeoutExpired:
        err = 'TIMEOUT'

    except Exception as e:
        err = 'UNKNOWN_EXC_ERROR'
        if sys.argv[1] == 'getverb': raise

        try:
            p = e.output
        except:
            p = ''
            
    return (err, p)


def findDiskTemp(p):
    resultA = None
    for i in temperaturePatterns:
        temperatureRe = re.search(i, p, re.I | re.M)
        if temperatureRe:
            resultA = temperatureRe.group(1)
            break

    return resultA


def findSerial(p):
    reSerial = re.search(r'^(?:\s+)?Serial Number:\s+(.+)', p, re.I | re.M)
    if reSerial:
        serial = reSerial.group(1)
    else:
        serial = None
        
    return serial


def chooseSystemSpecificPaths():

    if sys.platform.startswith('linux'):
        binPath_        = shlex.split(binPath_LINUX)
        agentConf_      = agentConf_LINUX
        senderPath_     = senderPath_LINUX
        senderPyPath_   = senderPyPath_LINUX

    elif sys.platform == 'win32':
        binPath_        = binPath_WIN
        agentConf_      = agentConf_WIN
        senderPath_     = senderPath_WIN
        senderPyPath_   = senderPyPath_WIN

    else:
        binPath_        = shlex.split(binPath_OTHER)
        agentConf_      = agentConf_OTHER
        senderPath_     = senderPath_OTHER
        senderPyPath_   = senderPyPath_OTHER

    if sys.argv[1] == 'getverb': 
        print('  Path guess: %s\n' % sys.platform)

    return (binPath_, agentConf_, senderPath_, senderPyPath_)


def isModelWithoutSensor(p):
    result = False
    for i in modelPatterns:
        modelRe = re.search(i, p, re.I | re.M)
        if modelRe:
            model = modelRe.group(1).strip()

            if model in noTemperatureSensorModels:
                result = True
                break

    return result
    
    
def isDummyNVMe(p):
    subsystemRe = re.search(r'Subsystem ID:\s+0x0000', p, re.I)
    ouiRe =       re.search(r'IEEE OUI Identifier:\s+0x000000', p, re.I)
    
    if     (subsystemRe and
            ouiRe):

        return True
    else:
        return False


if __name__ == '__main__':
    fail_ifNot_Py3()
    
    paths_Out = chooseSystemSpecificPaths()
    binPath = paths_Out[0]
    agentConf = paths_Out[1]
    senderPath = paths_Out[2]
    senderPyPath = paths_Out[3]

    host = sys.argv[2]
    senderData = []
    jsonData = []

    listDisks_Out = listDisks()
    scanErrors = listDisks_Out[0]
    diskList = listDisks_Out[1]

    scanErrorNotype = scanErrors[0]
    scanErrorNvme = scanErrors[1]

    sessionSerials = []
    allTemps = []
    diskError_NOCMD = False
    for d in diskList:
        clearedD = clearDiskTypeStr(d)
        sanitizedD = sanitizeStr(clearedD)
        jsonData.append({'{#DISK}':sanitizedD})

        disk_Out = findErrorsAndOuts(clearedD)
        diskError = disk_Out[0]
        diskPout = disk_Out[1]
        if diskError:
            if 'D_OS_' in diskError:
                diskError_NOCMD = diskError
                break   # other disks json are discarded

        isDuplicate = False
        serial = findSerial(diskPout)
        if serial in sessionSerials:
            isDuplicate = True
        elif serial:
            sessionSerials.append(serial)

        temp = findDiskTemp(diskPout)
        if isDuplicate:
            if isIgnoreDuplicates:
                driveStatus = 'DUPLICATE_IGNORE'
            else:
                driveStatus = 'DUPLICATE_MENTION'
        elif diskError:
            driveStatus = diskError
        elif isModelWithoutSensor(diskPout):
            driveStatus = 'NOSENSOR'
        elif isDummyNVMe(diskPout):
            driveStatus = 'DUMMY_NVME'
        elif not temp:
            driveStatus = 'NOTEMP'
        else:
            driveStatus = 'PROCESSED'
        senderData.append('"%s" mini.disk.info[%s,DriveStatus] "%s"' % (host, sanitizedD, driveStatus))

        if temp:
            senderData.append('"%s" mini.disk.temp[%s] "%s"' % (host, sanitizedD, temp))
            allTemps.append(temp)

        senderData.append('"%s" mini.disk.tempMin[%s] "%s"'  % (host, sanitizedD, thresholds[0][1]))
        senderData.append('"%s" mini.disk.tempMax[%s] "%s"'  % (host, sanitizedD, thresholds[0][2]))
        senderData.append('"%s" mini.disk.tempCrit[%s] "%s"' % (host, sanitizedD, thresholds[0][3]))

        if isHeavyDebug:
            heavyOut = repr(diskPout.strip())
            heavyOut = heavyOut.strip().strip('"').strip("'").strip()
            heavyOut = heavyOut.replace("'", r"\'").replace('"', r'\"')

            debugData = '"%s" mini.disk.HeavyDebug "%s"' % (host, heavyOut)
            if diskError:
                if 'ERR_CODE_' in diskError:
                    senderData.append(debugData)
            elif not temp:
                if not isModelWithoutSensor(diskPout):
                    senderData.append(debugData)

    if scanErrorNotype:
        configStatus = scanErrorNotype
    elif diskError_NOCMD:
        configStatus = diskError_NOCMD
    elif not diskList:
        configStatus = 'NODISKS'
    elif not allTemps:
        configStatus = 'NODISKTEMPS'
    else:
        configStatus = 'CONFIGURED'
    senderData.append('"%s" mini.disk.info[ConfigStatus] "%s"' % (host, configStatus))

    if allTemps:
        senderData.append('"%s" mini.disk.temp[MAX] "%s"' % (host, str(max(allTemps))))

    link = r'https://github.com/nobodysu/zabbix-mini-IPMI/issues'
    sendStatusKey = 'mini.disk.info[SendStatus]'
    processData(senderData, jsonData, agentConf, senderPyPath, senderPath, timeout, host, link, sendStatusKey)

