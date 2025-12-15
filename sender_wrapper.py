#!/usr/bin/env python3

import sys
import subprocess
import re
import os
from time import sleep
from json import dumps


def isWindows():

    if sys.platform == 'win32':
        return True
    else:
        return False

        
def send():
    """When running directly as '__main__'"""
    fetchMode = sys.argv[1]
    agentConf = sys.argv[2]
    senderPath = sys.argv[3]
    delay = int(sys.argv[4])
    senderDataNStr = sys.argv[5]
    additionalArgs = findDockerArgs()

    if isWindows():
        delay = 0

    if fetchMode == 'get':
        sleep(delay)   # wait for LLD to be processed by server
        cmd = [senderPath, '-c', agentConf, '-i', '-']
        cmd.extend(additionalArgs)
        senderProc = subprocess.Popen(cmd, stdin=subprocess.PIPE, universal_newlines=True, close_fds=(not isWindows()))

    elif fetchMode == 'getverb':
        print('\n  Note: the sender will fail if server did not gather LLD previously.', file=sys.stderr)
        print('\n  Data sent to zabbix sender:\n', file=sys.stderr)
        print(senderDataNStr)
        cmd = [senderPath, '-vv', '-c', agentConf, '-i', '-']
        cmd.extend(additionalArgs)
        senderProc = subprocess.Popen(cmd, stdin=subprocess.PIPE, universal_newlines=True, close_fds=(not isWindows()))

    else:
        print(f"{sys.argv[0]}: Not supported. Use 'get' or 'getverb'.", file=sys.stderr)
        sys.exit(1)

    senderProc.communicate(input=senderDataNStr)


def fail_ifNot_Py3():
    """Terminate if not using python3"""
    if sys.version_info.major != 3:
        sys.stdout.write(sys.argv[0] + ': Python3 is required.')
        sys.exit(1)


def oldPythonMsg():
    """Warn about REALLY old python version without timeout support in subprocess module"""
    if     (sys.version_info.major == 3 and
            sys.version_info.minor <= 2):
            
        print("python32 or less is detected. It's advisable to use python33 or above for timeout guards support.", file=sys.stderr)


def displayVersions(config, senderPath_):
    """Display python and sender versions"""
    print(f'  Python version:\n {sys.version}', file=sys.stderr)
    
    oldPythonMsg()

    try:
        print(f"\n  Sender version:\n {subprocess.check_output([senderPath_, '-V']).decode()}", file=sys.stderr)
    except Exception as e:
        print(e, file=sys.stderr)

    print('', file=sys.stderr)


def readConfig(config):
    """Deprecated because of unreliability"""

def chooseDevnull():
    """Universal DEVNULL to support REALLY old python versions"""
    try:
        from subprocess import DEVNULL   # for python versions greater than 3.3, inclusive
    except ImportError:
        import os
        DEVNULL = open(os.devnull, 'w')  # for 3.0-3.2, inclusive
 
    return DEVNULL


def findDockerArgs():
    """Find zabbix arguments from environment variables, but only if running in docker"""
    envToParam = {'ZBX_SERVER_HOST':          '-z',
                  'ZBX_TLSCONNECT':           '--tls-connect',
                  'ZBX_TLSCAFILE':            '--tls-ca-file',
                  'ZBX_TLSCRLFILE':           '--tls-crl-file',
                  'ZBX_TLSSERVERCERTISSUER':  '--tls-server-cert-issuer',
                  'ZBX_TLSSERVERCERTSUBJECT': '--tls-server-cert-subject',
                  'ZBX_TLSCERTFILE':          '--tls-cert-file',
                  'ZBX_TLSKEYFILE':           '--tls-key-file',
                  'ZBX_TLSPSKIDENTITY':       '--tls-psk-identity',
                  'ZBX_TLSPSKFILE':           '--tls-psk-file',
                  'ZBX_TLSCIPHERCERT13':      '--tls-cipher13',
                  'ZBX_TLSCIPHERCERT':        '--tls-cipher',
    }
    found = []

    if not os.path.isfile('/.dockerenv'):
        return found

    envVars = dict(os.environ)
    for k, v in envToParam.items():
        if k in envVars:
            found.append(v)
            found.append(envVars[k])

    return found

def processData(senderData_,
                jsonData_,
                agentConf_,
                senderPyPath_,
                senderPath_,
                delay_,
                host_,
                issuesLink_,
                sendStatusKey_='NOT_PROVIDED'):
    """Compose data and try to send it, when running imported"""
    DEVNULL = chooseDevnull()

    fetchMode_ = sys.argv[1]
    senderDataNStr = '\n'.join(senderData_)   # items for zabbix sender separated by newlines

    additionalArgs = findDockerArgs()

    # Pass senderDataNStr to sender_wrapper.py:
    if fetchMode_ == 'get':
        print(dumps({"data": jsonData_}, indent=4))   # print data gathered for LLD

        # Spawn new process and regain shell control immediately
        try:
            cmdPy = [sys.executable, senderPyPath_, fetchMode_, agentConf_, senderPath_, delay_, senderDataNStr]
            subprocess.Popen(cmdPy, stdin=subprocess.PIPE, stdout=DEVNULL, stderr=DEVNULL, close_fds=(not isWindows()))

        except OSError as e:
            if e.args[0] == 7:
                cmd = [senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', 'HUGEDATA']
                cmd.extend(additionalArgs)
                subprocess.call(cmd)
            else:
                cmd = [senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', 'SEND_OS_ERROR']
                cmd.extend(additionalArgs)
                subprocess.call(cmd)

        except Exception as e:
            cmd = [senderPath_, '-c', agentConf_, '-s', host_, '-k', sendStatusKey_, '-o', e]
            cmd.extend(additionalArgs)
            subprocess.call(cmd)

    elif fetchMode_ == 'getverb':
        displayVersions(agentConf_, senderPath_)

        #for i in range(135000): senderDataNStr = senderDataNStr + '0'   # HUGEDATA testing
        try:
            # Do not detach if in verbose mode, also skips delay in 'sender_wrapper.py'
            cmdPy = [sys.executable, senderPyPath_, 'getverb', agentConf_, senderPath_, delay_, senderDataNStr]
            subprocess.Popen(cmdPy, stdin=subprocess.PIPE, close_fds=(not isWindows()))

        except OSError as e:
            if e.args[0] == 7:   # dozens of disks
                print(f'{sys.argv[0]}: Could not send anything. Argument list or filepath too long. (HUGEDATA)', file=sys.stderr)   # FileNotFoundError: [WinError 206]
            else:
                print(f'{sys.argv[0]}: Something went wrong. (SEND_OS_ERROR)', file=sys.stderr)

            raise

        finally:
            print(f'  Please report any issues or empty results to:\n{issuesLink_}\n', file=sys.stderr)

    else:
        print(f"{sys.argv[0]}: Not supported. Use 'get' or 'getverb'.", file=sys.stderr)


def clearDiskTypeStr(s):
    """Some versions of smartctl returns empty result on incorrect device type"""
    stopWords = (
        (' -d atacam'), (' -d scsi'), (' -d ata'), (' -d sat'), (' -d nvme'), 
        (' -d sas'),    (' -d csmi'), (' -d usb'), (' -d pd'),  (' -d auto'),
    )

    for i in stopWords:
        s = s.replace(i, '')

    s = s.strip()

    return s


def removeQuotes(s):
    """Remove double or single quotes from a string"""
    quotes = ("'", '"')

    for i in quotes:
        s = s.replace(i, '')

    return s


def sanitizeStr(s):
    """Sanitizes provided string in sequential order.
    These strings cannot be used in zabbix macro and item names
    """
    stopChars = (
        ('/dev/', ''), (' -d', ''), ('   ', '_'), ('  ', '_'), (' ', '_'),
        ('!', '_'), (',', '_'), ('[', '_'), ('~', '_'),
        (']', '_'), ('+', '_'), ('/', '_'), ('\\', '_'), ('\'', '_'),
        ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'),
        ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'),
        ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'),
        ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'),
    )

    s = s.strip()

    for i, j in stopChars:
        s = s.replace(i, j)

    return s


if __name__ == '__main__':

    send()

