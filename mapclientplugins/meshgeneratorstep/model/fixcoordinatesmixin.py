from opencmiss.utils.maths import vectorops

from opencmiss.zinc.scenecoordinatesystem import SCENECOORDINATESYSTEM_LOCAL, \
    SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_CENTRE


class FixCoordinatesMixin(object):

    def __init__(self):
        self._fixed_coordinate_field = None
        self._fixed_projection_field = None
        self._stationary_projection_field = None

    def _updateAlignmentValues(self):
        fieldmodule = self._region.getFieldmodule()
        cache = fieldmodule.createFieldcache()
        _, t_matrix = self._scene.getTransformationMatrix()
        t_matrix = vectorops.reshape(t_matrix, (4, 4))
        _, projection = self._stationary_projection_field.evaluateReal(cache, 16)
        projection = vectorops.reshape(projection, (4, 4))
        projection = vectorops.matrixmult(t_matrix, projection)
        projection = vectorops.reshape(projection, -1)
        scale_vector = [vectorops.magnitude([projection[0], projection[4], projection[8]]),
                        vectorops.magnitude([projection[1], projection[5], projection[9]]),
                        vectorops.magnitude([projection[2], projection[6], projection[10]])]
        rotation_matrix = [[projection[0], projection[1], projection[2]],
                           [projection[4], projection[5], projection[6]],
                           [projection[8], projection[9], projection[10]]]
        xScale = scale_vector[0]
        yScale = scale_vector[1]
        zScale = scale_vector[2]
        rot_mx = [[projection[0]*xScale, projection[1]*yScale, projection[2]*zScale],
                           [projection[4]*xScale, projection[5]*yScale, projection[6]*zScale],
                           [projection[8]*xScale, projection[9]*yScale, projection[10]*zScale]]
        euler_angles = vectorops.rotationMatrix3ToEuler(rotation_matrix)
        eul_anlges = vectorops.rotationMatrix3ToEuler(rot_mx)
        offset_vector = [projection[3], projection[7], projection[11]]
        settings = {'euler_angles': eul_anlges, 'offset': offset_vector, 'scale': scale_vector}
        self.setAlignSettings(settings)

    def _updateFixedProjectionField(self):
        fieldmodule = self._region.getFieldmodule()
        fieldmodule.beginChange()
        cache = fieldmodule.createFieldcache()
        result, projection = self._ndc_projection_field.evaluateReal(cache, 16)
        self._fixed_projection_field.assignReal(cache, projection)
        fieldmodule.endChange()

    def setSceneviewer(self, sceneviewer):
        fieldmodule = self._region.getFieldmodule()
        fieldmodule.beginChange()
        self._ndc_projection_field = \
            fieldmodule.createFieldSceneviewerProjection(sceneviewer, SCENECOORDINATESYSTEM_LOCAL,
                                                         SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_CENTRE)
        p2 = fieldmodule.createFieldSceneviewerProjection(sceneviewer, SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_CENTRE,
                                                          SCENECOORDINATESYSTEM_LOCAL)
        self._stationary_projection_field = fieldmodule.createFieldMatrixMultiply(4, p2, self._fixed_projection_field)
        self._fixed_coordinate_field = fieldmodule.createFieldProjection(self._scaledCoordinateField,
                                                                         self._stationary_projection_field)
        fieldmodule.endChange()


