#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/mini-IPMI

# path to zabbix agent configuration file
agentConf = '/usr/local/etc/zabbix24/zabbix_agentd.conf'

import sys
import re
import subprocess

senderPath = 'zabbix_sender'
sysctlOut = subprocess.getoutput('sysctl dev.cpu')
trapperStdout = []
isDebug = ''

cpuTempRe = re.findall(r'dev\.cpu\.(\d+)\.temperature:\s+(\d+).\d+C', sysctlOut, re.I)

if cpuTempRe:
    coreMax = []
    for i, (b, a) in enumerate(cpuTempRe):
        coreMax.append(int(a))
        trapperStdout.append('- temp.cpu[' + b + '] ' + a)
    cmdStdout = max(coreMax)

## debug BEGIN
if len(sys.argv) > 1:                                                                      # if any argument is provided to the script
    if sys.argv[1].find('-v') != -1:                                                       # if first argument is '-v'
        if cpuTempRe:
            print('cpuTempRe:    ', cpuTempRe)
        print()

        try:
            openConf = open(agentConf, 'r')                                                # open config file
            openedConf = openConf.read()                                                   # make a str out of opened file
        except:
            print('temp-cpu-bsd: can\'t open config file!')
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
        print('temp-cpu-bsd: only \'-v\' is supported')
## debug END

trapperStdoutNStr = '\n'.join(trapperStdout)

senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, universal_newlines=True)
senderProc.communicate(input=trapperStdoutNStr)

if cpuTempRe:
    print(cmdStdout)
elif subprocess.getoutput('kldstat').find('temp.ko') != 1:
    print('temp-cpu-bsd: amdtemp or coretemp is not loaded')
else:
    print('temp-cpu-bsd: no sensor was found on proccessor')
