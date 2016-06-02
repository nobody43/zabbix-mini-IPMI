#!/usr/bin/env python3

## Cross-platform smartmontools temperature wrapper for Zabbix.
## Installation instructions: https://github.com/nobodysu/mini-IPMI

# provide raid configuration if needed
raidOverride = []
# like this:
#raidOverride = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

import sys
import re
import subprocess

if len(sys.argv) > 1:                                                                                # if any argument is provided to the script
    inputArg = sys.argv[1]                                                                           # assign a variable to the first argument
else:
    print('temp-disk: no argument')
    sys.exit(0)

if re.search('^max$|^max\.force$', inputArg) is not None:                                            # if 'temp.disk[max]' or 'temp.disk[max.force]' item is requested from zabbix
    isSingle = False
elif re.search('^\d+$|^\d+\.force$', inputArg) is not None:                                          # if specific disk, like 'temp.disk[0]'
    isSingle = True
else:
    print('temp-disk: wrong argument')
    sys.exit(0)

if inputArg.find('.force') != -1:                                                                    # if arg contains '.force' (forces a disk standby)
    isStandbyForce = True
else:
    isStandbyForce = False

allDisksStdout = subprocess.getoutput('smartctl --scan')                                             # get command output
if allDisksStdout.find('smartctl: not found') != -1 or allDisksStdout.find('\"smartctl\" ') != -1:   # if output contains specific words
    print('temp-disk: smartctl was not found in PATH')
    sys.exit(0)

diskList = re.findall(r'# (.*?), ', allDisksStdout)                                                  # form a list of disk paths from command output

if raidOverride:                                                                                     # check if raid override is provided
    diskList = raidOverride                                                                          # replace a list with predefined

if not diskList:
    print('temp-disk: no drives were found\nDoes smartctl have sudo access?')
    sys.exit(0)

tempList = []                                                                                        # create an empty list for future appending
diskListSingle = []

#print('diskList(all):    ', diskList) ## DEBUG

if isSingle == True:                                                                                 # if single disk was selected previously
    diskNumber = re.match('(\d+)', inputArg)                                                         # find numeric value in argument
    try:                                                                                             # try to
        diskListSingle.append(diskList[int(diskNumber.group(1))])                                    # get position in 'diskList' based on provided disk number
    except:                                                                                          # if no such position exists - print and exit
        print('temp-disk: no such disk')
        sys.exit(0)
    diskList = diskListSingle                                                                        # replace list to process with previous calculations

#print('diskList(proc):   ', diskList) ## DEBUG 

for i in diskList:                                                                                   # start a loop through full disk names
#    print('processing:       ', i) ## DEBUG
    if isStandbyForce == False:                                                                      # if no '.force' option was provided previously
        isStandby = subprocess.getoutput('smartctl --nocheck standby -i ' + i)                       # check if device is in standby mode
        if isStandby.find('evice is in STANDBY mode') != -1:
            if isSingle == True:                                                                     # if its a single disk check
                print('temp-disk: ' + i + ' is in STANDBY mode')                                     # print info and exit
                sys.exit(0)
            continue                                                                                 # if string is present in output - go to the next disk
    tempStdout = subprocess.getoutput('smartctl -l scttempsts ' + i)                                 # check temperature with sct command
    tempRe = re.search(r'Current Temperature:\s+(\d+) Celsius', tempStdout, re.I)                    # search for temperature value case insensitively
    if tempRe is not None:                                                                           # if value was found
        tempList.append(int(tempRe.group(1)))                                                        # append to the temperature list converting str to int
    elif tempStdout.find('ermission denied') != -1 or tempStdout.find('missing admin rights') != -1: # if no value was found and certain string was found in output
        print('temp-disk: smartctl does not have sudo/admin access')
        sys.exit(0)
    elif tempStdout.find('SCT Commands not supported') != -1:                                        # if string is present in output (old drives)
        stdoutAll = subprocess.getoutput('smartctl -A ' + i)                                         # check temperature alternatively with full output
        stdoutAllRe = re.search('Temperature_Celsius\s+\w+\s+\d+\s+\d+\s+\d+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)\s', stdoutAll, re.I)
        if stdoutAllRe is not None:                                                                  # if value was found
            tempList.append(int(stdoutAllRe.group(1)))
if tempList:                                                                                         # if list of all temperatures is not empty
#    print('tempList:         ', tempList) ## DEBUG
    print(max(tempList))                                                                             # calculate max temperature from list (gathered by appending) and print value
else:                                                                                                # if list is empty
    print('temp-disk: could not get temperature from drive(s)\nIs sensor present?')
