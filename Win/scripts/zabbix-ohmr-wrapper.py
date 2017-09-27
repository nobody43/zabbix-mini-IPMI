## OpenHardwareMonitorReport wrapper for Zabbix.
## This script will not work without configuring file paths and properly configured zabbix agent config.
## Also, OHMR requires .NET Framework.
## Installation instructions: https://github.com/nobodysu/mini-IPMI

# path to OpenHardwareMonitorReport binary with forward slashes
OHMR = 'C:/distr/OpenHardwareMonitorReport/OpenHardwareMonitorReport.exe'
# path to zabbix agent configuration file with forward slashes
agentConf = 'C:/zabbix_agentd.conf'
# path to zabbix sender binary with forward slashes
senderPath = 'C:/zabbix-agent/bin/win32/zabbix_sender.exe'

import sys
import re
import subprocess

reportOut = subprocess.getoutput(OHMR)                                                    # get output from process specified earlier 
trapperStdout = []
isDebug = ''

boardTempRe = re.findall(r':\s+(\d+)\s+\d+\s+\d+\s+\(\/lpc\/[\w-]+\/temperature\/(\d+)\)', reportOut, re.I)    # find all matching strings in output, and add value and index number to tuple list case insensitively
cpuTempRe = re.findall(r'CPU\sCore\s+#\d+\s+:\s+(\d+)\s+\d+\s+\d+\s+\(\/[\w-]+cpu\/\d+\/temperature\/(\d+)\)', reportOut, re.I)
gpuTempRe = re.findall(r':\s+(\d+)\s+\d+\s+\d+\s+\(\/[\w-]+gpu\/\d+\/temperature\/(\d+)\)', reportOut, re.I)
boardFanRe = re.findall(r':\s+(\d+)(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\(\/lpc\/[\w-]+\/fan\/(\d+)\)', reportOut, re.I)
gpuFanRe = re.findall(r':\s+(\d+)(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\(\/[\w-]+gpu\/[\w-]+\/fan\/(\d+)\)', reportOut, re.I)
voltageRe = re.findall(r':\s+(\d+\.\d+)\s+\d+\.\d+\s+\d+\.\d+\s+\(\/lpc\/[\w-]+\/voltage\/(\d+)\)', reportOut, re.I)

if boardTempRe:                                                                            # if list 'boardTempRe' is not empty
    boardMax = []                                                                          # create an empty list for future appending
    for i, (a, b) in enumerate(boardTempRe):                                               # loop through tuple list 'boardTempRe'
        boardMax.append(int(a))                                                            # append value 'a' from tuple to list 'boardMax' for calculating max temperature
        trapperStdout.append('- temp.brd[' + b + '] ' + a)                                 # make a string from value 'a' and position 'b' and append it to list for zabbix sender
    trapperStdout.append('- temp.brd[max] ' + str(max(boardMax)))                          # calculate and append max temperature for zabbix sender

if cpuTempRe:
    coreMax = []
    for i, (a, b) in enumerate(cpuTempRe):
        coreMax.append(int(a))
        trapperStdout.append('- temp.cpu[' + b + '] ' + a)
    cmdStdout = max(coreMax)                                                               # do not append, save in separate var for stdout

if gpuTempRe:
    videoMax = []
    for i, (a, b) in enumerate(gpuTempRe):
        videoMax.append(int(a))
        trapperStdout.append('- temp.gpu[' + b + '] ' + a)
    trapperStdout.append('- temp.gpu[max] ' + str(max(videoMax)))

if boardFanRe:
    for i, (a, b) in enumerate(boardFanRe):
        trapperStdout.append('- fan.brd[' + b + '] ' + a)

if gpuFanRe:
    for i, (a, b) in enumerate(gpuFanRe):
        trapperStdout.append('- fan.gpu[' + b + '] ' + a)

if voltageRe:
    for i, (a, b) in enumerate(voltageRe):
        trapperStdout.append('- vlt.brd[' + b + '] ' + a)

## debug BEGIN
if len(sys.argv) > 1:                                                                      # if any argument is provided to the script
    if sys.argv[1].find('-v') != -1:                                                       # if first argument is '-v'
        if boardTempRe:
            print('boardTempRe:  ', boardTempRe)
        if cpuTempRe:
            print('cpuTempRe:    ', cpuTempRe)
        if gpuTempRe:
            print('gpuTempRe:    ', gpuTempRe)
        if boardFanRe:
            print('boardFanRe:   ', boardFanRe)
        if gpuFanRe:
            print('gpuFanRe:     ', gpuFanRe)
        if voltageRe:
            print('voltageRe:    ', voltageRe)
        print()

        try:
            openConf = open(agentConf, 'r')                                                # open config file
            openedConf = openConf.read()                                                   # make a str out of opened file
        except:
            print('zabbix-ohmr-wrapper: can\'t open config file!')
            sys.exit(0)
        confHostRe = re.search(r'(?:\n|^)Hostname=(.+)\n', openedConf, re.I | re.M)        # multiline case insensitive search for 'Hostname' value
        confServerRe = re.search(r'(?:\n|^)ServerActive=(.+)\n', openedConf, re.I | re.M)
        openConf.close()                                                                   # remember to close it
        if confServerRe is not None:
            print('  ServerActive config value:\n' + confServerRe.group(1) + '\n')
        else:
            print('  No ServerActive value was found inside zabbix config file!\n')

        if confHostRe is not None:
            print('  Hostname config value:\n' + confHostRe.group(1) + '\n')
        else:
            print('  No Hostname value was found inside zabbix config file!\n')

        try:
            import shutil
            print('  zabbix_sender path:\n' + shutil.which(senderPath) + '\n')
        except:
            print('  zabbix_sender path:\n' + senderPath + '\nwas not found!\n')
            sys.exit(0)

        isDebug = '-vv'                                                                    # add verbose key to sender output
        print('  Data sent to zabbix sender:')
        for i in trapperStdout:                                                            # print all gathered items that go to zabbix sender
            print(i)

        print()
    else:
        print('zabbix-ohmr-wrapper: only \'-v\' is supported')
## debug END

trapperStdoutNStr = '\n'.join(trapperStdout)                                               # join all list values into one string separated by newlines

senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, universal_newlines=True) # execute command with data from stdin, dump stdout and provide string instead of bytes
senderProc.communicate(input=trapperStdoutNStr)                                            # provide stdin and send data from 'trapperStdoutNStr' to zabbix server

if cpuTempRe:
    print(cmdStdout)
else:
    print('zabbix-ohmr-wrapper: no sensor was found on proccessor')
