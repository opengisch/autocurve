"""
This script starts the test suite from within QGIS.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

import sys
import unittest

from qgis.PyQt.QtCore import qDebug
from qgis.utils import iface

# TODO: proper tests discovery
from autocurve.tests import tests_integration

# Foward pyqgis output to console
sys.stdout.write = lambda text: qDebug(text.strip())
sys.stderr.write = lambda text: qDebug(text.strip())

print("Waiting for initialisation...")


def run_tests():

    print("Starting tests...")

    # Run the tests
    test = unittest.main(module=tests_integration, exit=False)

    # To workaround missing exit code (see below), so we print the result value and check for it in the runner
    if test.result.wasSuccessful():
        print("__SUCCESS__")
    else:
        print("__FAILURE__")

    # Exit code here is lost, since this crashes QGIS with segfault
    print("notice: following `QGIS died on signal 11` can be ignored.")
    sys.exit(0 if test.result.wasSuccessful() else 1)


# Start tests only once init is complete
iface.initializationCompleted.connect(run_tests)
