from qgis.core import (
    QgsFeatureRequest,
    QgsGeometry,
    QgsGeometryUtils,
    QgsPoint,
    QgsVectorLayer,
    QgsVertexId,
)

from . import settings
from .log import debug, log


def harmonize_arcs_centers(layer: QgsVectorLayer):

    for feature in layer.selectedFeatures():

        debug(f"Arc snapping ft. {feature.id()}...")

        # Find all arcs points
        arcs_vertices = _get_curve_points(feature.geometry())

        # Skip if not curved
        if not arcs_vertices:
            debug(f"  no arc vertices segments, skipping")
            continue

        # Find all neighbours to test against
        request = QgsFeatureRequest()
        request.setDistanceWithin(feature.geometry(), 0.001)
        neighbours = layer.getFeatures(request)

        # Iterate and check for snapping
        for arc_vertex in arcs_vertices:
            debug(f"  Doing arc vertex {arc_vertex}")

            for neighbour in neighbours:
                if neighbour.id() == feature.id():
                    continue

                debug(f"    testing against ft. {neighbour.id()}")

                for nearby_arc_vertex in _get_curve_points(neighbour.geometry()):

                    if _can_snap(feature, arc_vertex, neighbour, nearby_arc_vertex):
                        other_vertex = neighbour.geometry().vertexAt(nearby_arc_vertex)
                        new_geom = QgsGeometry(feature.geometry())
                        success = new_geom.moveVertex(other_vertex, arc_vertex)
                        if not success:
                            log(f"Error while snaping at {other_vertex}")
                        layer.dataProvider().changeGeometryValues(
                            {feature.id(): new_geom}
                        )
                        debug(f"      pt. {nearby_arc_vertex}: SNAP")
                    else:
                        debug(f"      pt. {nearby_arc_vertex}: NO SNAP")


def _can_snap(
    feature_1: QgsGeometry, arc_vertex_1: int, feature_2: QgsGeometry, arc_vertex_2: int
):
    """Returns whether both given vertices can snap."""
    # For now, we only snap if the start and end point are equal

    v_1a, v_1c = feature_1.geometry().adjacentVertices(arc_vertex_1)
    v_2a, v_2c = feature_2.geometry().adjacentVertices(arc_vertex_2)

    p1a = feature_1.geometry().vertexAt(v_1a)
    p1b = feature_1.geometry().vertexAt(arc_vertex_1)
    p1c = feature_1.geometry().vertexAt(v_1c)

    p2a = feature_2.geometry().vertexAt(v_2a)
    p2b = feature_1.geometry().vertexAt(arc_vertex_2)
    p2c = feature_2.geometry().vertexAt(v_2c)

    # Test if start and end points are equal
    if not (p1a == p2a and p1c == p2c) or (p1a == p2c and p1c == p2a):
        return False

    # Test if circles are equivalent (same center point within tolerance)
    _, c1x, c1y = QgsGeometryUtils.circleCenterRadius(p1a, p1b, p1c)
    _, c2x, c2y = QgsGeometryUtils.circleCenterRadius(p2a, p2b, p2c)
    c1 = QgsPoint(c1x, c1y)
    c2 = QgsPoint(c2x, c2y)
    return c1.distance(c2) < settings.DISTANCE


def _get_curve_points(geometry):
    curved_vertices = []
    vertex_id = QgsVertexId()
    while True:
        found, point = geometry.constGet().nextVertex(vertex_id)
        if not found:
            break
        if vertex_id.type is QgsVertexId.VertexType.Curve:
            curved_vertices.append(geometry.vertexNrFromVertexId(vertex_id))

    return curved_vertices
