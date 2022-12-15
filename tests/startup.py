"""
This script starts the test suite.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

import sys
import unittest

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import qDebug
from qgis.utils import iface


class QtLogger:
    def write(self, text):
        qDebug(text.strip())

    def flush(self):
        pass


sys.stdout = QtLogger()


def run_tests():
    sys.path.append("/tests_directory")
    import autocurve_tests

    tests = unittest.main(module=autocurve_tests, exit=False)

    success = tests.result.wasSuccessful()

    # none of these exits
    # QgsApplication.exit(not success)
    # QApplication.exit(not success)
    # QCoreApplication.exit(not success)

    # crashes with `double free or corruption (out)` -> exit code 127
    QgsApplication.instance().exitQgis()
    sys.exit(not success)


iface.initializationCompleted.connect(run_tests)
