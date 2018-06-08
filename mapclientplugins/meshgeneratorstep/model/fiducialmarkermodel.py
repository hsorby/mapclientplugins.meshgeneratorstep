from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph

from opencmiss.utils.zinc import createFiniteElementField
from opencmiss.utils.maths import vectorops

import numpy as np


class FiducialMarkerModel(object):

    def __init__(self, region):
        self._get_labels = None
        self._get_plane_info = None
        self._enabled = False
        self._parent_region = region
        self._region_name = 'fiducial'
        self._markers = {}
        self._settings = {'display-fiducial-markers': True,
                          'active-marker-label': ''}
        self._clear()

    def registerGetPlaneInfoMethod(self, method):
        self._get_plane_info = method

    def registerGetFiducialLabelsMethod(self, method):
        self._get_labels = method

    def getPlaneDescription(self):
        plane_normal, _, point_on_plane = self._get_plane_info()
        return point_on_plane, plane_normal

    def setDisplayFiducialMarkers(self, state):
        self._settings['display-fiducial-markers'] = state
        if self._scene is not None:
            self._scene.setVisibilityFlag(state)

    def isDisplayFiducialMarkers(self):
        return self._settings['display-fiducial-markers']

    def setActiveMarker(self, marker_label):
        self._settings['active-marker-label'] = marker_label

    def getActiveMarker(self):
        return self._settings['active-marker-label']

    def getSettings(self):
        return self._settings

    def setSettings(self, settings):
        self._settings.update(settings)

    def isEnabled(self):
        return self._enabled

    def setNodeLocation(self, position):
        adjusted_position = self._getSceneTransformationToAdjustedPosition(position)
        marker = self._markers[self._settings['active-marker-label']]
        marker.setPosition(adjusted_position)

    def getMarkerLocation(self, label):
        marker = self._markers[label]
        return self._getSceneTransformationFromAdjustedPosition(marker.getPosition())

    def setMarkerLocation(self, label, position):
        new_position = self._getSceneTransformationToAdjustedPosition(position)
        marker = self._markers[label]
        marker.setPosition(new_position)

    def _getSceneTransformationFromAdjustedPosition(self, position):
        matrix = self.getSceneTransformationMatrix()
        matrix = vectorops.reshape(matrix, (4, 4))
        new_position = vectorops.mxvectormult(matrix, [*position, 1])
        new_position = vectorops.div(new_position[:3], new_position[3])
        return new_position

    def _getSceneTransformationToAdjustedPosition(self, position):
        matrix = self.getSceneTransformationMatrix()
        matrix = vectorops.reshape(matrix, (4, 4))
        inv_matrix = np.linalg.inv(matrix)
        new_position = vectorops.mxvectormult(inv_matrix.tolist(), [*position, 1])
        new_position = vectorops.div(new_position[:3], new_position[3])
        return new_position

    def isReadyForFitting(self):
        for marker_label in self._markers:
            marker = self._markers[marker_label]
            if not marker.isDefined():
                return False

        return True if len(self._markers) > 0 else False

    def reset(self):
        transformation_matrix = None
        if self._region:
            transformation_matrix = self.getSceneTransformationMatrix()
            self._parent_region.removeChild(self._region)
        self._region = self._parent_region.createChild(self._region_name)
        if transformation_matrix is not None:
            self.setSceneTransformationMatrix(transformation_matrix)
        self._scene = self._region.getScene()
        labels = self._get_labels()
        if labels is not None:
            self._createModel(labels)
            self._enabled = True
        else:
            self._enabled = False

    def getSceneTransformationMatrix(self):
        scene = self._region.getScene()
        _, matrix = scene.getTransformationMatrix()
        return matrix

    def setSceneTransformationMatrix(self, matrix):
        if self._region is not None:
            scene = self._region.getScene()
            scene.setTransformationMatrix(matrix)

    def _createModel(self, labels):
        for label in labels:
            self._markers[label] = FiducialMarker(self._region, label)

    def _clear(self):
        self._region = None
        self._scene = None
        self._get_plane_info = None
        self._get_labels = None


def _createGraphics(scene, coordinate_field, label):
    scene.beginChange()
    scene.removeAllGraphics()
    materialmodule = scene.getMaterialmodule()
    blue = materialmodule.findMaterialByName('blue')
    graphic = scene.createGraphicsPoints()
    graphic.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
    graphic.setCoordinateField(coordinate_field)
    graphic.setMaterial(blue)
    label_graphic = scene.createGraphicsPoints()
    label_graphic.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
    label_graphic.setCoordinateField(coordinate_field)
    attributes = graphic.getGraphicspointattributes()
    attributes.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
    attributes.setBaseSize([0.02])
    label_attributes = label_graphic.getGraphicspointattributes()
    label_attributes.setBaseSize([0.02])
    label_attributes.setLabelText(1, label)
    label_attributes.setLabelOffset([1.0, -0.2, 0.0])
    scene.endChange()

    return graphic


class FiducialMarker(object):

    def __init__(self, region, label):
        self._region = region.createChild(label)
        self._coordinate_field = createFiniteElementField(self._region)
        self._fieldmodule = self._region.getFieldmodule()
        self._label = label
        # self._label_field = self._fieldmodule.createFieldStoredString()
        scene = self._fieldmodule.getRegion().getScene()
        self._graphic = _createGraphics(scene, self._coordinate_field, label)
        self._node = None

    def _create(self):
        nodeset = self._fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        template = nodeset.createNodetemplate()
        template.defineField(self._coordinate_field)
        # template.defineField(self._label_field)
        self._node = nodeset.createNode(-1, template)
        self._group_field = self._fieldmodule.createFieldGroup()
        node_group = self._group_field.createFieldNodeGroup(nodeset)
        self._nodeset_group = node_group.getNodesetGroup()

    def setPosition(self, position):
        if self._node is None:
            self._create()
        fieldcache = self._fieldmodule.createFieldcache()
        self._fieldmodule.beginChange()
        fieldcache.setNode(self._node)
        self._coordinate_field.assignReal(fieldcache, position)
        # self._label_field.assignString(fieldcache, self._label)
        self._fieldmodule.endChange()

    def getPosition(self):
        fieldcache = self._fieldmodule.createFieldcache()
        self._fieldmodule.beginChange()
        fieldcache.setNode(self._node)
        _, position = self._coordinate_field.evaluateReal(fieldcache, 3)
        # self._label_field.assignString(fieldcache, self._label)
        self._fieldmodule.endChange()

        return position

    def isDefined(self):
        return self._node is not None
