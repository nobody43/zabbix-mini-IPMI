#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# SPDX-License-Identifier: GPL-3.0-only

import unittest
import pathlib
import json
from mini_ipmi_lmsensors import *


class outputData():
    """File reader"""
    def __init__(self, filePath):
        self.filePath = filePath
        self.output = self.readFile()

    def readFile(self):
        try:
            with open(self.filePath, 'r', encoding='utf-8') as file:
                print(f'  {self.filePath}: opened')
                return file.read()

        except FileNotFoundError:
            print(f'  {self.filePath}: not found')


class simpleTests(unittest.TestCase):

    def test_isIgnoredMbSensor(self):

        self.assertIsNotNone(isIgnoredMbSensor('', ''))
        self.assertTrue(isIgnoredMbSensor('nct6791-isa-0290', 'AUXTIN3'))
        self.assertFalse(isIgnoredMbSensor('nct6791-isa-0291', 'AUXTIN3'))
        self.assertFalse(isIgnoredMbSensor('nct6791-isa-0290', 'AUXTIN2'))


class parsingTests(unittest.TestCase):

    def setUp(self): 
        self.maxDiff = None

    def test_main(self):
        """Load 'sensors -u' output from a file and
           search for results of main function in corresponding '*_items.txt' and '*_lld.txt'
        """
        lmsensorsDir = pathlib.Path('outputs/lmsensors')
        allOutputFiles = [f for f in lmsensorsDir.iterdir() if f.is_file() and f.match('*.txt')]
 
        for p in allOutputFiles:
            lmsensorsOut = outputData(p)
            print(lmsensorsOut.output)
            print()

            lldPath   = pathlib.Path('results/lmsensors/' + lmsensorsOut.filePath.stem + '_lld.txt')
            itemsPath = pathlib.Path('results/lmsensors/' + lmsensorsOut.filePath.stem + '_items.txt')

            lldFileOut   = outputData(lldPath).output
            itemsFileOut = outputData(itemsPath).output

            (jsonData, senderData) = main(lmsensorsOut.output, 'TEST_STATUS', 'Example host')
            prettyJsonData   = json.dumps(jsonData, indent=4)
            prettySenderData = json.dumps(senderData, indent=4)
            print(f"  {lldPath}: expected contents:")
            print(prettyJsonData)
            print(f"  {itemsPath}: expected contents:")
            print(prettySenderData)
 
            try:
                correspondingJson   = json.loads(lldFileOut)
            except json.decoder.JSONDecodeError as e:
                print(f"  {lldPath}:, {e}")

            try:
                correspondingItems = json.loads(itemsFileOut)
            except json.decoder.JSONDecodeError as e:
                print(f"  {itemsPath}:, {e}")

            self.assertEqual(main(lmsensorsOut.output, 'TEST_STATUS', 'Example host'), (correspondingJson, correspondingItems))
 

if __name__ == '__main__':

    unittest.main()

