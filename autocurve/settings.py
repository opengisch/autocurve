from qgis.core import QgsSettings

DISTANCE_KEY = "/qgis/digitizing/convert_to_curve_distance_tolerance"
ANGLE_KEY = "/qgis/digitizing/convert_to_curve_angle_tolerance"
CURVIFY_ENABLED_KEY = "autocurve/curvify_enabled"
HARMONIZE_ENABLED_KEY = "autocurve/harmonize_enabled"


def distance():
    return float(QgsSettings().value(DISTANCE_KEY, 1e-6))


def angle():
    return float(QgsSettings().value(ANGLE_KEY, 1e-6))


def autocurve_enabled():
    return QgsSettings().value(CURVIFY_ENABLED_KEY, None) == "true"


def set_autocurve_enabled(value):
    QgsSettings().setValue(CURVIFY_ENABLED_KEY, str(value).lower())


def harmonize_enabled():
    return QgsSettings().value(HARMONIZE_ENABLED_KEY, None) == "true"


def set_harmonize_enabled(value):
    QgsSettings().setValue(HARMONIZE_ENABLED_KEY, str(value).lower())
