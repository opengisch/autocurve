"""
This script starts the test suite.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

import sys
import unittest

from qgis.PyQt.QtCore import qDebug
from qgis.utils import iface


class QtLogger:
    def write(self, text):
        qDebug(text.strip())


sys.stdout = QtLogger()


def run_tests():
    print("AAAAAAAAAAAa")
    sys.path.append("/tests_directory")
    import autocurve_tests

    print("BBBBBBBB")
    tests = unittest.main(module=autocurve_tests, exit=False)

    success = tests.result.wasSuccessful()

    # QgsApplication.exit(not success)  # does not quit
    # QApplication.exit(not success)  # does not quit
    # QCoreApplication.exit(not success)  # does not quit

    # crashes with `double free or corruption (out)` -> exit code 127
    sys.exit(not success)


iface.initializationCompleted.connect(run_tests)
