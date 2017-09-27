#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/mini-IPMI

# path to zabbix agent configuration file
agentConf = '/etc/zabbix/zabbix_agentd.conf'

import sys
import re
import subprocess

senderPath = 'zabbix_sender'
sensorsOut = subprocess.getoutput('sensors')
trapperStdout = []
isDebug = ''

boardTempRe = re.findall(r'Temperature:\s+\+(\d+)\.\d', sensorsOut, re.I)
cpuTempRe = re.findall(r'(?:Core\s+\d+|Core\d+\s+Temp):\s+\+(\d+)\.\d', sensorsOut, re.I)
gpuTempRe = re.findall(r'Adapter: \w+ adapter\ntemp\d+:\s+\+(\d+)\.\d', sensorsOut, re.I | re.M)    # ignoring the case and searching multiple lines
boardFanRe = re.findall(r'FAN Speed:\s+(\d+)\s+RPM', sensorsOut, re.I)
voltageRe = re.findall(r'\+(\d+\.\d+)\s+V\s', sensorsOut, re.I)

if boardTempRe:                                                                            # if list 'boardTempRe' is not empty
    while '0' in boardFanRe: boardFanRe.remove('0')                                        # ommit zero values
    boardMax = []                                                                          # create an empty list for future appending
    for i, a in enumerate(boardTempRe):                                                    # loop through tuple list 'boardTempRe'
        boardMax.append(int(a))                                                            # append value 'a' from tuple to list 'boardMax' for calculating max temperature
        trapperStdout.append('- temp.brd[' + str(i) + '] ' + a)                            # make a string from value 'a' and position 'b' and append it to list for zabbix sender
    trapperStdout.append('- temp.brd[max] ' + str(max(boardMax)))                          # calculate and append max temperature for zabbix sender

if cpuTempRe:
    coreMax = []
    for i, a in enumerate(cpuTempRe):
        coreMax.append(int(a))
        trapperStdout.append('- temp.cpu[' + str(i) + '] ' + a)
    cmdStdout = max(coreMax)                                                               # do not append, save in separate var for stdout

if gpuTempRe:
    videoMax = []
    for i, a in enumerate(gpuTempRe):
        videoMax.append(int(a))
        trapperStdout.append('- temp.gpu[' + str(i) + '] ' + a)
    trapperStdout.append('- temp.gpu[max] ' + str(max(videoMax)))

if boardFanRe:
    for i, a in enumerate(boardFanRe):
        trapperStdout.append('- fan.brd[' + str(i) + '] ' + a)

if voltageRe:
    for i, a in enumerate(voltageRe):
        trapperStdout.append('- vlt.brd[' + str(i) + '] ' + a)

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
        if voltageRe:
            print('voltageRe:    ', voltageRe)
        print()

        try:
            openConf = open(agentConf, 'r')                                                # open config file
            openedConf = openConf.read()                                                   # make a str out of opened file
        except:
            print('zabbix-lmsensors-wrapper: can\'t open config file!')
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
        print('zabbix-lmsensors-wrapper: only \'-v\' is supported')
## debug END

trapperStdoutNStr = '\n'.join(trapperStdout)

senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, universal_newlines=True)
senderProc.communicate(input=trapperStdoutNStr)

if cpuTempRe:
    print(cmdStdout)
elif sensorsOut.find('sensors: command not found') != -1:
    print('zabbix-lmsensors-wrapper: sensors was not found in PATH')
else:
    print('zabbix-lmsensors-wrapper: no sensor was found on proccessor')
