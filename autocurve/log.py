from qgis.core import Qgis, QgsMessageLog


def log(message, level=Qgis.MessageLevel.Warning):
    QgsMessageLog.logMessage(
        message,
        "AutoCurve",
        notifyUser=level in [Qgis.MessageLevel.Warning, Qgis.MessageLevel.Critical],
    )


def debug(message):
    log(message, level=Qgis.MessageLevel.Info)
