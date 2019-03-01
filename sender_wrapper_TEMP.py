#!/usr/bin/env python3

import sys
import subprocess
import re
from time import sleep
from json import dumps


def send():
    agentConf = sys.argv[2]
    senderPath = sys.argv[3]
    timeout = int(sys.argv[4])
    senderDataNStr = sys.argv[5]

    if sys.platform == 'win32':   # if windows
        timeout = 0   # probably permanent workaround

    if sys.argv[1] == 'get':
        sleep(timeout)   # wait for LLD to be processed by server
        senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, universal_newlines=True)   # send data gathered from second argument to zabbix server
    elif sys.argv[1] == 'getverb':
        print('\n  Note: the sender will fail if server did not gather LLD previously.')
        print('\n  Data sent to zabbix sender:\n')
        print(senderDataNStr)
        senderProc = subprocess.Popen([senderPath, '-vv', '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, universal_newlines=True)   # verbose sender output
    else:
        print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
        sys.exit(1)

    senderProc.communicate(input=senderDataNStr)


if __name__ == '__main__':
    send()


# external
def fail_ifNot_Py3():
    '''Terminate if not using python3.'''
    if sys.version_info.major != 3:
        sys.stdout.write(sys.argv[0] + ': Python3 is required.')
        sys.exit(1)


def displayVersions(config, senderP):
    '''Display python and sender versions.'''
    print('  Python version:\n', sys.version)

    try:
        print('\n  Sender version:\n', subprocess.check_output([senderP, '-V']).decode())
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


def processData(sender, json, conf, pyP, senderP, tout, hn, issuesLink):
    '''Compose data and try to send it.'''
    try:
        from subprocess import DEVNULL   # for python versions greater than 3.3, inclusive
    except:
        import os
        DEVNULL = open(os.devnull, 'w')  # for 3.0-3.2, inclusive

    senderDataNStr = '\n'.join(sender)   # items for zabbix sender separated by newlines

    # pass senderDataNStr to sender_wrapper.py:
    if sys.argv[1] == 'get':
        print(dumps({"data": json}, indent=4))   # print data gathered for LLD

        # spawn new process and regain shell control immediately (on Win 'sender_wrapper.py' will not wait)
        try:
            subprocess.Popen([sys.executable, pyP, 'get', conf, senderP, tout, senderDataNStr], stdin=subprocess.PIPE, stdout=DEVNULL, stderr=DEVNULL)

        except OSError as e:
            if e.args[0] == 7:
                subprocess.call([senderP, '-c', conf, '-s', hn, '-k', 'mini.disk.info[ConfigStatus]', '-o', 'HUGEDATA'])
            else:
                subprocess.call([senderP, '-c', conf, '-s', hn, '-k', 'mini.disk.info[ConfigStatus]', '-o', 'SEND_OS_ERROR'])

        except:
            subprocess.call([senderP, '-c', conf, '-s', hn, '-k', 'mini.disk.info[ConfigStatus]', '-o', 'UNKNOWN_SEND_ERROR'])

    elif sys.argv[1] == 'getverb':
        displayVersions(conf, senderP)
        readConfig(conf)

        #for i in range(135000): senderDataNStr = senderDataNStr + '0'   # HUGEDATA testing
        try:
            # do not detach if in verbose mode, also skips timeout in 'sender_wrapper.py'
            subprocess.Popen([sys.executable, pyP, 'getverb', conf, senderP, tout, senderDataNStr], stdin=subprocess.PIPE)

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
            print('  Please report any issues or missing features to:\n%s\n' % issuesLink)

    else:
        print(sys.argv[0] + ": Not supported. Use 'get' or 'getverb'.")


def replaceStr(s):
    '''Sanitizes provided string in correct order.'''
    stopChars = (('/dev/', ''), (' -d atacam', ''), (' -d scsi', ''), (' -d ata', ''), (' -d sat', ''), (' -d sas', ''), (' -d auto', ''),
                 (' -d', ''), ('!', '_'), (',', '_'), ('[', '_'), ('~', '_'),
                 (']', '_'), ('+', '_'), ('  ', ' '), ('/', '_'), ('\\', '_'),
                 ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'),
                 ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'),
                 ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'),
                 ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'), (' ', '_'))

    for i, j in stopChars:
        s = s.replace(i, j)
    return s
