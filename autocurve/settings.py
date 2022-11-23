from qgis.core import QgsSettings


class _Settings:
    @property
    def distance(self):
        return float(
            QgsSettings().value(
                "/qgis/digitizing/convert_to_curve_distance_tolerance", 1e-6
            )
        )

    @property
    def angle(self):
        return float(
            QgsSettings().value(
                "/qgis/digitizing/convert_to_curve_angle_tolerance", 1e-6
            )
        )

    @property
    def autocurve_enabled(self):
        return QgsSettings().value("autocurve/curvify_enabled", None) == "true"

    @autocurve_enabled.setter
    def autocurve_enabled(self, value):
        QgsSettings().setValue("autocurve/curvify_enabled", str(value).lower())

    @property
    def harmonize_enabled(self):
        return QgsSettings().value("autocurve/harmonize_enabled", None) == "true"

    @harmonize_enabled.setter
    def harmonize_enabled(self, value):
        QgsSettings().setValue("autocurve/harmonize_enabled", str(value).lower())


Settings = _Settings()
