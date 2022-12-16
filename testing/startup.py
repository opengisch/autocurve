"""
This script starts the test suite from within QGIS.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

import sys
import unittest

from qgis.PyQt.QtCore import qDebug
from qgis.utils import iface

import autocurve_tests

# Foward python output to console
sys.stdout.write = lambda text: qDebug(text.strip())


def run_tests():
    # Run the tests
    test = unittest.main(module=autocurve_tests, exit=False)

    # To workaround missing exit code (see below), so we print the result value and check for it in the runner
    if test.result.wasSuccessful():
        print("__TESTS_SUCCESSFUL__")

    # Exit code here is lost, since this crashes QGIS with segfault
    sys.exit(0 if test.result.wasSuccessful() else 1)


# Start tests only once init is complete
iface.initializationCompleted.connect(run_tests)
