"""
This script starts the test suite.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

import sys
import unittest

from qgis.PyQt.QtCore import qDebug
from qgis.utils import iface

import autocurve_tests


class QtLogger:
    def write(self, text):
        qDebug(text.strip())

    def flush(self):
        pass


sys.stdout = QtLogger()


def run_tests():
    unittest.main(module=autocurve_tests)


iface.initializationCompleted.connect(run_tests)
