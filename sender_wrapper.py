#!/usr/bin/env python3

import sys
import subprocess
import re
from time import sleep
from json import dumps


def isWindows():
    if sys.platform == 'win32':
        return True
    else:
        return False

        
def send():

    if fetchMode == 'get':
        sleep(timeout)   # wait for LLD to be processed by server
        senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'],
                                      stdin=subprocess.PIPE, universal_newlines=True, close_fds=(not isWindows()))

    elif fetchMode == 'getverb':
        print('\n  Note: the sender will fail if server did not gather LLD previously.')
        print('\n  Data sent to zabbix sender:')
        print('\n')
        print(senderDataNStr)
        senderProc = subprocess.Popen([senderPath, '-vv', '-c', agentConf, '-i', '-'],
                                      stdin=subprocess.PIPE, universal_newlines=True, close_fds=(not isWindows()))

    else:
        print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
        sys.exit(1)

    senderProc.communicate(input=senderDataNStr)


if __name__ == '__main__':
    fetchMode = sys.argv[1]

    agentConf = sys.argv[2]
    senderPath = sys.argv[3]
    timeout = int(sys.argv[4])
    senderDataNStr = sys.argv[5]

    if isWindows():
        timeout = 0

    send()


# External
def fail_ifNot_Py3():
    '''Terminate if not using python3.'''
    if sys.version_info.major != 3:
        sys.stdout.write(sys.argv[0] + ': Python3 is required.')
        sys.exit(1)


def oldPythonMsg():
    if     (sys.version_info.major == 3 and
            sys.version_info.minor <= 2):
            
        print("python32 or less is detected. It's advisable to use python33 or above for timeout guards support.")


def displayVersions(config, senderPath_):
    '''Display python and sender versions.'''
    print('  Python version:\n', sys.version)
    
    oldPythonMsg()

    try:
        print('\n  Sender version:\n', subprocess.check_output([senderPath_, '-V']).decode())
    except:
        print('Could not run zabbix_sender.')

    print()


def readConfig(config):
    '''Read and display important config values for debug.'''
    try:
        f = open(config, 'r')
        text = f.read()
        f.close()

        print("  Config's main settings:")
        server = re.search(r'^(?:\s+)?(Server(?:\s+)?\=(?:\s+)?.+)$', text, re.M)
        if server:
            print(server.group(1))
        else:
            print("Could not find 'Server' setting in config!")

        serverActive = re.search(r'^(?:\s+)?(ServerActive(?:\s+)?\=(?:\s+)?.+)$', text, re.M)
        if serverActive:
            print(serverActive.group(1))
        else:
            print("Could not find 'ServerActive' setting in config!")

        timeout = re.search(r'^(?:\s+)?(Timeout(?:\s+)?\=(?:\s+)?(\d+))(?:\s+)?$', text, re.M)
        if timeout:
            print(timeout.group(1))

            if int(timeout.group(2)) < 10:
                print("'Timeout' setting is too low for this script!")
        else:
            print("Could not find 'Timeout' manual setting in config!\nDefault value is too low for this script.")

    except:
        print('  Could not process config file:\n' + config)
    finally:
        print()


def chooseDevnull():
    try:
        from subprocess import DEVNULL   # for python versions greater than 3.3, inclusive
    except:
        import os
        DEVNULL = open(os.devnull, 'w')  # for 3.0-3.2, inclusive
        
    return DEVNULL


def processData(senderData_, jsonData_, agentConf_, senderPyPath_, senderPath_,
                timeout_, host_, issuesLink_, sendStatusKey_='UNKNOWN'):
    '''Compose data and try to send it.'''
    DEVNULL = chooseDevnull()

    fetchMode_ = sys.argv[1]
    senderDataNStr = '\n'.join(senderData_)   # items for zabbix sender separated by newlines

    # pass senderDataNStr to sender_wrapper.py:
    if fetchMode_ == 'get':
        print(dumps({"data": jsonData_}, indent=4))   # print data gathered for LLD

        # spawn new process and regain shell control immediately (on Win 'sender_wrapper.py' will not wait)
        try:
            cmd = [sys.executable, senderPyPath_, fetchMode_, agentConf_, senderPath_, timeout_, senderDataNStr]
        
            subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=DEVNULL, stderr=DEVNULL, close_fds=(not isWindows()))

        except OSError as e:
            if e.args[0] == 7:
                subprocess.call([senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', 'HUGEDATA'])
            else:
                subprocess.call([senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', 'SEND_OS_ERROR'])

        except:
            subprocess.call(    [senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', 'UNKNOWN_SEND_ERROR'])

    elif fetchMode_ == 'getverb':
        displayVersions(agentConf_, senderPath_)
        readConfig(agentConf_)

        #for i in range(135000): senderDataNStr = senderDataNStr + '0'   # HUGEDATA testing
        try:
            # do not detach if in verbose mode, also skips timeout in 'sender_wrapper.py'
            cmd = [sys.executable, senderPyPath_, 'getverb', agentConf_, senderPath_, timeout_, senderDataNStr]
            
            subprocess.Popen(cmd, stdin=subprocess.PIPE, close_fds=(not isWindows()))

        except OSError as e:
            if e.args[0] == 7:   # almost unreachable in case of this script
                print(sys.argv[0] + ': Could not send anything. Argument list or filepath too long. (HUGEDATA)')   # FileNotFoundError: [WinError 206]
            else:
                print(sys.argv[0] + ': Something went wrong. (SEND_OS_ERROR)')

            raise

        except:
            print(sys.argv[0] + ': Something went wrong. (UNKNOWN_SEND_ERROR)')
            raise

        finally:
            print('  Please report any issues or missing features to:\n%s\n' % issuesLink_)

    else:
        print(sys.argv[0] + ": Not supported. Use 'get' or 'getverb'.")


def clearDiskTypeStr(s):
    stopWords = (
        (' -d atacam'), (' -d scsi'), (' -d ata'), (' -d sat'), (' -d nvme'), 
        (' -d sas'),    (' -d csmi'), (' -d usb'), (' -d pd'),  (' -d auto'),
    )

    for i in stopWords:
        s = s.replace(i, '')

    s = s.strip()

    return s


def removeQuotes(s):
    quotes = ('\'', '"')

    for i in quotes:
        s = s.replace(i, '')

    return s


def sanitizeStr(s):
    '''Sanitizes provided string in sequential order.'''
    stopChars = (
        ('/dev/', ''), (' -d', ''),
        ('!', '_'), (',', '_'), ('[', '_'), ('~', '_'), ('  ', '_'),
        (']', '_'), ('+', '_'), ('/', '_'), ('\\', '_'), ('\'', '_'),
        ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'),
        ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'),
        ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'),
        ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'), (' ', '_'),
    )

    for i, j in stopChars:
        s = s.replace(i, j)

    s = s.strip()

    return s
