"""
This script starts the test suite.

It should be mounted to ~/.local/share/QGIS/QGIS3/startup.py to run the tests on QGIS startup.
"""

from qgis.utils import iface


def run_tests():
    iface.messageBar().pushMessage("Info", "Running tests...")


iface.initializationCompleted.connect(run_tests)
