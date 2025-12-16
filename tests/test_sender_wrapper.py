#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# SPDX-License-Identifier: GPL-3.0-only

import unittest
import os
from unittest.mock import patch
from sender_wrapper import *


class simpleTests(unittest.TestCase):

    def test_removeQuotes(self):

        self.assertEqual(removeQuotes('9tSXaR'), '9tSXaR')
        self.assertEqual(removeQuotes('"9tSXaR'), '9tSXaR')
        self.assertEqual(removeQuotes('ZqA7D9"'), 'ZqA7D9')
        self.assertEqual(removeQuotes("'XgEU3p"), 'XgEU3p')
        self.assertEqual(removeQuotes("amN35r'"), 'amN35r')
        self.assertEqual(removeQuotes("'amN35r'"), 'amN35r')
        self.assertEqual(removeQuotes('"amN35r"'), 'amN35r')
        self.assertEqual(removeQuotes('  "amN35r" '), '  amN35r ')
        self.assertEqual(removeQuotes('9uZ"3hh\'5h"TY\'MQ '), '9uZ3hh5hTYMQ ')
        self.assertEqual(removeQuotes('9uZ"3hh\' 5h"TY\'MQ '), '9uZ3hh 5hTYMQ ')
        self.assertEqual(removeQuotes("FgE'\"\"'gKR'o\"'\"Ad'''n9\"\"\"x42qADvsF'"), 'FgEgKRoAdn9x42qADvsF')

    def test_sanitizeStr(self):

        self.assertEqual(sanitizeStr('/dev/sda'), 'sda')
        self.assertEqual(sanitizeStr('/dev/csmi0,0 -d ata'), 'csmi0_0_ata')
        self.assertEqual(sanitizeStr(' /dev/csmi0,0 -d ata  '), 'csmi0_0_ata')
        self.assertEqual(sanitizeStr('/dev/csmi0,0'), 'csmi0_0')
        self.assertEqual(sanitizeStr('/dev/sda -d scsi'), 'sda_scsi')
        self.assertEqual(sanitizeStr('/dev/nvme0 -d nvme'), 'nvme0_nvme')
        self.assertEqual(sanitizeStr('/dev/sda['), 'sda_')
        self.assertEqual(sanitizeStr('/dev/sda"'), 'sda_')
        self.assertEqual(sanitizeStr("/dev/sda'"), 'sda_')
        self.assertEqual(sanitizeStr("/dev/sda' "), 'sda_')
        self.assertEqual(sanitizeStr("/dev/sda\\"), 'sda_')
        self.assertEqual(sanitizeStr("/dev/sda\\\\"), 'sda__')

    def test_clearDiskTypeStr(self):

        self.assertEqual(clearDiskTypeStr('/dev/nvme1 -d nvme '), '/dev/nvme1')
        self.assertEqual(clearDiskTypeStr('/dev/csmi0,0 -d ata '), '/dev/csmi0,0')
        self.assertEqual(clearDiskTypeStr('/dev/sdb -d auto '), '/dev/sdb')
        self.assertEqual(clearDiskTypeStr('   /dev/sdb -d auto  '), '/dev/sdb')

    @patch.dict(os.environ, {"ZBX_SERVER_HOST": "192.168.0.2"})
    def test_findDockerArgs_NOT_docker(self):

        # Empty result on non-docker, even with imitated env
        self.assertEqual(findDockerArgs(), [])

    @patch.dict(os.environ, {"ZBX_SERVER_HOST": "192.168.0.3"})
    @patch.dict(os.environ, {"ZBX_TLSPSKIDENTITY": "Example host"})
    @patch('os.path.isfile')
    def test_findDockerArgs_docker(self, mock_isfile):
        """Imitate docker with additional env variables"""
        mock_isfile.return_value = True
 
        # Additional arguments for sender on docker with env variables
        self.assertEqual(findDockerArgs(), ['-z', '192.168.0.3', '--tls-psk-identity', 'Example host'])
        mock_isfile.assert_called_once_with('/.dockerenv')


if __name__ == '__main__':

    unittest.main()

