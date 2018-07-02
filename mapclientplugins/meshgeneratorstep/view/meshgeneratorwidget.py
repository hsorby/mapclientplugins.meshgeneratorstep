"""
Created on Aug 29, 2017

@author: Richard Christie
"""
import types
import numpy as np

from PySide import QtGui, QtCore
from functools import partial

from mapclientplugins.meshgeneratorstep.view.ui_meshgeneratorwidget import Ui_MeshGeneratorWidget
from opencmiss.utils.maths import vectorops


FMA_ROLE = QtCore.Qt.UserRole + 1


class MeshGeneratorWidget(QtGui.QWidget):

    def __init__(self, model, parent=None):
        super(MeshGeneratorWidget, self).__init__(parent)
        self._ui = Ui_MeshGeneratorWidget()
        self._ui.setupUi(self)
        self._model = model
        self._model.registerTimeValueUpdateCallback(self._updateTimeValue)
        self._model.registerFrameIndexUpdateCallback(self._updateFrameIndex)
        self._generator_model = model.getGeneratorModel()
        self._plane_model = model.getPlaneModel()
        self._fiducial_marker_model = model.getFiducialMarkerModel()
        self._annotation_model = model.getMeshAnnotationModel()
        self._ui.sceneviewer_widget.setContext(model.getContext())
        self._ui.sceneviewer_widget.setModel(self._plane_model)
        self._model.registerSceneChangeCallback(self._sceneChanged)
        self._doneCallback = None
        self._populateAnnotationTree()
        self._populateFiducialMarkersComboBox()
        self._marker_mode_active = False
        self._have_images = False
        meshTypeNames = self._generator_model.getAllMeshTypeNames()
        for meshTypeName in meshTypeNames:
            self._ui.meshType_comboBox.addItem(meshTypeName)
        self._makeConnections()

    def _graphicsInitialized(self):
        """
        Callback for when SceneviewerWidget is initialised
        Set custom scene from model
        """
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            self._model.loadSettings()
            self._refreshOptions()
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            # self._ui.sceneviewer_widget.setSelectModeAll()
            sceneviewer.setLookatParametersNonSkew([2.0, -2.0, 1.0], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0])
            sceneviewer.setTransparencyMode(sceneviewer.TRANSPARENCY_MODE_SLOW)
            self._autoPerturbLines()
            self._viewAll()

    def _sceneChanged(self):
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            if self._have_images:
                self._plane_model.setSceneviewer(sceneviewer)
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            self._autoPerturbLines()

    def _autoPerturbLines(self):
        """
        Enable scene viewer perturb lines iff solid surfaces are drawn with lines.
        Call whenever lines, surfaces or translucency changes
        """
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            sceneviewer.setPerturbLinesFlag(self._generator_model.needPerturbLines())

    def _makeConnections(self):
        self._ui.sceneviewer_widget.graphicsInitialized.connect(self._graphicsInitialized)
        self._ui.done_button.clicked.connect(self._doneButtonClicked)
        self._ui.viewAll_button.clicked.connect(self._viewAll)
        self._ui.meshType_comboBox.currentIndexChanged.connect(self._meshTypeChanged)
        self._ui.deleteElementsRanges_lineEdit.returnPressed.connect(self._deleteElementRangesLineEditChanged)
        self._ui.deleteElementsRanges_lineEdit.editingFinished.connect(self._deleteElementRangesLineEditChanged)
        self._ui.scale_lineEdit.returnPressed.connect(self._scaleLineEditChanged)
        self._ui.scale_lineEdit.editingFinished.connect(self._scaleLineEditChanged)
        self._ui.displayAxes_checkBox.clicked.connect(self._displayAxesClicked)
        self._ui.displayElementNumbers_checkBox.clicked.connect(self._displayElementNumbersClicked)
        self._ui.displayLines_checkBox.clicked.connect(self._displayLinesClicked)
        self._ui.displayNodeDerivatives_checkBox.clicked.connect(self._displayNodeDerivativesClicked)
        self._ui.displayNodeNumbers_checkBox.clicked.connect(self._displayNodeNumbersClicked)
        self._ui.displaySurfaces_checkBox.clicked.connect(self._displaySurfacesClicked)
        self._ui.displaySurfacesExterior_checkBox.clicked.connect(self._displaySurfacesExteriorClicked)
        self._ui.displaySurfacesTranslucent_checkBox.clicked.connect(self._displaySurfacesTranslucentClicked)
        self._ui.displaySurfacesWireframe_checkBox.clicked.connect(self._displaySurfacesWireframeClicked)
        self._ui.displayXiAxes_checkBox.clicked.connect(self._displayXiAxesClicked)
        self._ui.activeModel_comboBox.currentIndexChanged.connect(self._activeModelChanged)
        self._ui.toImage_pushButton.clicked.connect(self._imageButtonClicked)
        self._ui.displayImagePlane_checkBox.clicked.connect(self._displayImagePlaneClicked)
        self._ui.fixImagePlane_checkBox.clicked.connect(self._fixImagePlaneClicked)
        self._ui.timeValue_doubleSpinBox.valueChanged.connect(self._timeValueChanged)
        self._ui.timePlayStop_pushButton.clicked.connect(self._timePlayStopClicked)
        self._ui.frameIndex_spinBox.valueChanged.connect(self._frameIndexValueChanged)
        self._ui.framesPerSecond_spinBox.valueChanged.connect(self._framesPerSecondValueChanged)
        self._ui.timeLoop_checkBox.clicked.connect(self._timeLoopClicked)
        self._ui.displayFiducialMarkers_checkBox.clicked.connect(self._displayFiducialMarkersClicked)
        self._ui.fiducialMarker_comboBox.currentIndexChanged.connect(self._fiducialMarkerChanged)
        self._ui.fiducialMarkerTransform_pushButton.clicked.connect(self._fiducialMarkerTransformClicked)
        self._ui.annotation_treeWidget.itemChanged.connect(self._annotationItemChanged)

    def _fitToScaffold(self):
        # Get the fiducial marker points and their corresponding mesh points.
        labels = self._annotation_model.getFiducialMarkerLabels()
        node_locations = []
        marker_locations = []
        for label in labels:
            node_id = self._annotation_model.getNode(label)
            node_location = self._generator_model.getNodeLocation(node_id)
            marker_location = self._fiducial_marker_model.getMarkerLocation(label)
            node_locations.append(node_location)
            marker_locations.append(marker_location)

        # Formulate matrices
        source = np.matrix(marker_locations)
        target = np.matrix(node_locations)

        rotation_mx, translation_vec = rigid_transform_3D(source.T, target.T)

        N = source.shape[0]
        alt_transformed_source = rotation_mx*source.T + np.tile(translation_vec, (1, N))

        transformed_source = alt_transformed_source.T.tolist()
        for index, label in enumerate(labels):
            position = transformed_source[index]
            self._fiducial_marker_model.setMarkerLocation(label, position)

        plane_node_locations = np.matrix(self._plane_model.getNodeLocations())

        M = plane_node_locations.shape[0]
        new_plane_node_locations = rotation_mx*plane_node_locations.T + np.tile(translation_vec, (1, M))
        self._plane_model.setNodeLocations(new_plane_node_locations.T.tolist())

    def _fiducialMarkerTransformClicked(self):
        ready = self._fiducial_marker_model.isReadyForFitting()
        if ready:
            self._fitToScaffold()
        else:
            print('Fiducial markers are not ready for fitting.')

    def _fiducialMarkerChanged(self):
        self._fiducial_marker_model.setActiveMarker(self._ui.fiducialMarker_comboBox.currentText())

    def _displayFiducialMarkersClicked(self):
        self._fiducial_marker_model.setDisplayFiducialMarkers(self._ui.displayFiducialMarkers_checkBox.isChecked())

    def _populateFiducialMarkersComboBox(self):
        fiducial_marker_labels = self._annotation_model.getFiducialMarkerLabels()
        if fiducial_marker_labels is not None:
            self._ui.fiducialMarker_comboBox.addItems(self._annotation_model.getFiducialMarkerLabels())

    @staticmethod
    def _createFMAItem(parent, text, fma_id):
        item = QtGui.QTreeWidgetItem(parent)
        item.setText(0, text)
        item.setData(0, FMA_ROLE, fma_id)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)

        return item

    def _populateAnnotationTree(self):
        tree = self._ui.treeWidgetAnnotation
        tree.clear()
        rsh_item = self._createFMAItem(tree, 'right side of heart', 'FMA_7165')
        self._createFMAItem(rsh_item, 'ventricle', 'FMA_7098')
        self._createFMAItem(rsh_item, 'atrium', 'FMA_7096')
        self._createFMAItem(rsh_item, 'auricle', 'FMA_7218')
        lsh_item = self._createFMAItem(tree, 'left side of heart', 'FMA_7166')
        self._createFMAItem(lsh_item, 'ventricle', 'FMA_7101')
        self._createFMAItem(lsh_item, 'atrium', 'FMA_7097')
        self._createFMAItem(lsh_item, 'auricle', 'FMA_7219')
        apex_item = self._createFMAItem(tree, 'apex of heart', 'FMA_7164')
        vortex_item = self._createFMAItem(tree, 'vortex of heart', 'FMA_84628')

        self._ui.treeWidgetAnnotation.addTopLevelItem(rsh_item)
        self._ui.treeWidgetAnnotation.addTopLevelItem(lsh_item)
        self._ui.treeWidgetAnnotation.addTopLevelItem(apex_item)
        self._ui.treeWidgetAnnotation.addTopLevelItem(vortex_item)

    def _populateAnnotationTree(self):
        tree = self._ui.annotation_treeWidget
        tree.setHeaderHidden(True)
        tree.clear()
        labels = self._annotation_model.getAnnotationLabels()
        for label in labels:
            item = self._createFMAItem(tree, label[0], label[1])
            tree.addTopLevelItem(item)

    def getModel(self):
        return self._model

    def registerDoneExecution(self, doneCallback):
        self._doneCallback = doneCallback

    def _updateUi(self):
        if self._have_images:
            frame_count = self._plane_model.getFrameCount()
            self._ui.numFramesValue_label.setText("{0}".format(frame_count))
            self._ui.frameIndex_spinBox.setMaximum(frame_count)
            self._ui.timeValue_doubleSpinBox.setMaximum(frame_count / self._model.getFramesPerSecond())
        else:
            self._generator_model.disableAlignment()
            self._plane_model.disableAlignment()
            self._ui.alignment_groupBox.setVisible(False)
            self._ui.fiducialMarkers_groupBox.setVisible(False)
            self._ui.video_groupBox.setVisible(False)
            self._ui.displayImagePlane_checkBox.setVisible(False)
            self._ui.displayFiducialMarkers_checkBox.setVisible(False)

    def setImageInfo(self, image_info):
        self._plane_model.setImageInfo(image_info)
        self._fiducial_marker_model.reset()
        self._have_images = image_info is not None
        self._updateUi()

    def _doneButtonClicked(self):
        self._ui.dockWidget.setFloating(False)
        self._model.done()
        self._model = None
        self._doneCallback()

    def _imageButtonClicked(self):
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        normal, up, offset = self._plane_model.getPlaneInfo()
        _, current_lookat_pos = sceneviewer.getLookatPosition()
        _, current_eye_pos = sceneviewer.getEyePosition()
        view_distance = vectorops.magnitude(vectorops.sub(current_eye_pos, current_lookat_pos))
        eye_pos = vectorops.add(vectorops.mult(normal, view_distance), offset)
        lookat_pos = offset
        sceneviewer.setLookatParametersNonSkew(eye_pos, lookat_pos, up)

    def _updateTimeValue(self, value):
        self._ui.timeValue_doubleSpinBox.blockSignals(True)
        frame_count = self._plane_model.getFrameCount()
        max_time_value = frame_count / self._ui.framesPerSecond_spinBox.value()
        if value > max_time_value:
            self._ui.timeValue_doubleSpinBox.setValue(max_time_value)
            self._timePlayStopClicked()
        else:
            self._ui.timeValue_doubleSpinBox.setValue(value)
        self._ui.timeValue_doubleSpinBox.blockSignals(False)

    def _updateFrameIndex(self, value):
        self._ui.frameIndex_spinBox.blockSignals(True)
        self._ui.frameIndex_spinBox.setValue(value)
        self._ui.frameIndex_spinBox.blockSignals(False)

    def _timeValueChanged(self, value):
        self._model.setTimeValue(value)

    def _timeDurationChanged(self, value):
        self._model.setTimeDuration(value)

    def _timePlayStopClicked(self):
        play_text = 'Play'
        stop_text = 'Stop'
        current_text = self._ui.timePlayStop_pushButton.text()
        if current_text == play_text:
            self._ui.timePlayStop_pushButton.setText(stop_text)
            self._model.play()
        else:
            self._ui.timePlayStop_pushButton.setText(play_text)
            self._model.stop()

    def _timeLoopClicked(self):
        self._model.setTimeLoop(self._ui.timeLoop_checkBox.isChecked())

    def _frameIndexValueChanged(self, value):
        self._model.setFrameIndex(value)

    def _framesPerSecondValueChanged(self, value):
        self._model.setFramesPerSecond(value)
        self._ui.timeValue_doubleSpinBox.setMaximum(self._plane_model.getFrameCount()/value)

    def _fixImagePlaneClicked(self):
        self._plane_model.setImagePlaneFixed(self._ui.fixImagePlane_checkBox.isChecked())

    def _displayImagePlaneClicked(self):
        self._plane_model.setImagePlaneVisible(self._ui.displayImagePlane_checkBox.isChecked())

    def _activeModelChanged(self, index):
        if index == 0:
            self._ui.sceneviewer_widget.setModel(self._plane_model)
        else:
            self._ui.sceneviewer_widget.setModel(self._generator_model)

    def _meshTypeChanged(self, index):
        meshTypeName = self._ui.meshType_comboBox.itemText(index)
        self._generator_model.setMeshTypeByName(meshTypeName)
        self._fiducial_marker_model.reset()
        self._refreshMeshTypeOptions()

    def _meshTypeOptionCheckBoxClicked(self, checkBox):
        self._generator_model.setMeshTypeOption(checkBox.objectName(), checkBox.isChecked())

    def _meshTypeOptionLineEditChanged(self, lineEdit):
        self._generator_model.setMeshTypeOption(lineEdit.objectName(), lineEdit.text())
        finalValue = self._generator_model.getMeshTypeOption(lineEdit.objectName())
        lineEdit.setText(str(finalValue))

    def _refreshMeshTypeOptions(self):
        layout = self._ui.meshTypeOptions_frame.layout()
        # remove all current mesh type widgets
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
              child.widget().deleteLater()
        optionNames = self._generator_model.getMeshTypeOrderedOptionNames()
        for key in optionNames:
            value = self._generator_model.getMeshTypeOption(key)
            # print('key ', key, ' value ', value)
            if type(value) is bool:
                checkBox = QtGui.QCheckBox(self._ui.meshTypeOptions_frame)
                checkBox.setObjectName(key)
                checkBox.setText(key)
                checkBox.setChecked(value)
                callback = partial(self._meshTypeOptionCheckBoxClicked, checkBox)
                checkBox.clicked.connect(callback)
                layout.addWidget(checkBox)
            else:
                label = QtGui.QLabel(self._ui.meshTypeOptions_frame)
                label.setObjectName(key)
                label.setText(key)
                layout.addWidget(label)
                lineEdit = QtGui.QLineEdit(self._ui.meshTypeOptions_frame)
                lineEdit.setObjectName(key)
                lineEdit.setText(str(value))
                callback = partial(self._meshTypeOptionLineEditChanged, lineEdit)
                lineEdit.returnPressed.connect(callback)
                lineEdit.editingFinished.connect(callback)
                layout.addWidget(lineEdit)

        self._ui.fiducialMarker_comboBox.clear()
        self._ui.annotation_treeWidget.clear()
        self._populateAnnotationTree()
        self._populateFiducialMarkersComboBox()

    def _refreshOptions(self):
        self._ui.identifier_label.setText('Identifier:  ' + self._model.getIdentifier())
        self._ui.deleteElementsRanges_lineEdit.setText(self._generator_model.getDeleteElementsRangesText())
        self._ui.scale_lineEdit.setText(self._generator_model.getScaleText())
        self._ui.displayAxes_checkBox.setChecked(self._generator_model.isDisplayAxes())
        self._ui.displayElementNumbers_checkBox.setChecked(self._generator_model.isDisplayElementNumbers())
        self._ui.displayLines_checkBox.setChecked(self._generator_model.isDisplayLines())
        self._ui.displayNodeDerivatives_checkBox.setChecked(self._generator_model.isDisplayNodeDerivatives())
        self._ui.displayNodeNumbers_checkBox.setChecked(self._generator_model.isDisplayNodeNumbers())
        self._ui.displaySurfaces_checkBox.setChecked(self._generator_model.isDisplaySurfaces())
        self._ui.displaySurfacesExterior_checkBox.setChecked(self._generator_model.isDisplaySurfacesExterior())
        self._ui.displaySurfacesTranslucent_checkBox.setChecked(self._generator_model.isDisplaySurfacesTranslucent())
        self._ui.displaySurfacesWireframe_checkBox.setChecked(self._generator_model.isDisplaySurfacesWireframe())
        self._ui.displayXiAxes_checkBox.setChecked(self._generator_model.isDisplayXiAxes())
        self._ui.displayImagePlane_checkBox.setChecked(self._plane_model.isDisplayImagePlane())
        self._ui.displayFiducialMarkers_checkBox.setChecked(self._fiducial_marker_model.isDisplayFiducialMarkers())
        self._ui.fixImagePlane_checkBox.setChecked(self._plane_model.isImagePlaneFixed())
        self._ui.framesPerSecond_spinBox.setValue(self._model.getFramesPerSecond())
        self._ui.timeLoop_checkBox.setChecked(self._model.isTimeLoop())
        index = self._ui.meshType_comboBox.findText(self._generator_model.getMeshTypeName())
        self._ui.meshType_comboBox.blockSignals(True)
        self._ui.meshType_comboBox.setCurrentIndex(index)
        self._ui.meshType_comboBox.blockSignals(False)
        index = self._ui.fiducialMarker_comboBox.findText(self._fiducial_marker_model.getActiveMarker())
        self._ui.fiducialMarker_comboBox.blockSignals(True)
        self._ui.fiducialMarker_comboBox.setCurrentIndex(0 if index == -1 else index)
        self._ui.fiducialMarker_comboBox.blockSignals(False)
        self._refreshMeshTypeOptions()

    def _deleteElementRangesLineEditChanged(self):
        self._generator_model.setDeleteElementsRangesText(self._ui.deleteElementsRanges_lineEdit.text())
        self._ui.deleteElementsRanges_lineEdit.setText(self._generator_model.getDeleteElementsRangesText())

    def _scaleLineEditChanged(self):
        self._generator_model.setScaleText(self._ui.scale_lineEdit.text())
        self._ui.scale_lineEdit.setText(self._generator_model.getScaleText())

    def _displayAxesClicked(self):
        self._generator_model.setDisplayAxes(self._ui.displayAxes_checkBox.isChecked())

    def _displayElementNumbersClicked(self):
        self._generator_model.setDisplayElementNumbers(self._ui.displayElementNumbers_checkBox.isChecked())

    def _displayLinesClicked(self):
        self._generator_model.setDisplayLines(self._ui.displayLines_checkBox.isChecked())
        self._autoPerturbLines()

    def _displayNodeDerivativesClicked(self):
        self._generator_model.setDisplayNodeDerivatives(self._ui.displayNodeDerivatives_checkBox.isChecked())

    def _displayNodeNumbersClicked(self):
        self._generator_model.setDisplayNodeNumbers(self._ui.displayNodeNumbers_checkBox.isChecked())

    def _displaySurfacesClicked(self):
        self._generator_model.setDisplaySurfaces(self._ui.displaySurfaces_checkBox.isChecked())
        self._autoPerturbLines()

    def _displaySurfacesExteriorClicked(self):
        self._generator_model.setDisplaySurfacesExterior(self._ui.displaySurfacesExterior_checkBox.isChecked())

    def _displaySurfacesTranslucentClicked(self):
        self._generator_model.setDisplaySurfacesTranslucent(self._ui.displaySurfacesTranslucent_checkBox.isChecked())
        self._autoPerturbLines()

    def _displaySurfacesWireframeClicked(self):
        self._generator_model.setDisplaySurfacesWireframe(self._ui.displaySurfacesWireframe_checkBox.isChecked())

    def _displayXiAxesClicked(self):
        self._generator_model.setDisplayXiAxes(self._ui.displayXiAxes_checkBox.isChecked())

    def _annotationItemChanged(self, item):
        fmaTerm = item.data(0, FMA_ROLE)
        # for now we ignore "parent" items and let the tree widget handle selection
        if item.childCount() == 0:
            self._generator_model.highlightDomain(fmaTerm, item.checkState(0) == QtCore.Qt.Checked)

        # Debug
        # if item.checkState(0) == QtCore.Qt.Checked:
        #     print("FMA term selected: {0}".format(fmaTerm))
        # elif item.checkState(0) == QtCore.Qt.PartiallyChecked:
        #     print("FMA term partially selected: {0}".format(fmaTerm))
        # else:
        #     print("FMA term unselected: {0}".format(fmaTerm))

    def _viewAll(self):
        """
        Ask sceneviewer to show all of scene.
        """
        if self._ui.sceneviewer_widget.getSceneviewer() is not None:
            self._ui.sceneviewer_widget.viewAll()

    def keyPressEvent(self, event):
        if event.modifiers() & QtCore.Qt.CTRL and \
                self._fiducial_marker_model.isEnabled() and \
                        QtGui.QApplication.mouseButtons() == QtCore.Qt.NoButton:
            self._marker_mode_active = True
            self._ui.sceneviewer_widget._model = self._fiducial_marker_model
            self._original_mousePressEvent = self._ui.sceneviewer_widget.mousePressEvent
            self._original_mouseMoveEvent = self._ui.sceneviewer_widget.mouseMoveEvent
            self._original_mouseReleaseEvent = self._ui.sceneviewer_widget.mouseReleaseEvent
            self._ui.sceneviewer_widget._calculatePointOnPlane = \
                types.MethodType(_calculatePointOnPlane, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mousePressEvent = types.MethodType(mousePressEvent, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mouseMoveEvent = types.MethodType(mouseMoveEvent, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mouseReleaseEvent = \
                types.MethodType(mouseReleaseEvent, self._ui.sceneviewer_widget)
            self._model.printLog()

    def keyReleaseEvent(self, event):
        if self._marker_mode_active:
            self._marker_mode_active = False
            self._ui.sceneviewer_widget._model = self._plane_model
            self._ui.sceneviewer_widget._calculatePointOnPlane = None
            self._ui.sceneviewer_widget.mousePressEvent = self._original_mousePressEvent
            self._ui.sceneviewer_widget.mouseMoveEvent = self._original_mouseMoveEvent
            self._ui.sceneviewer_widget.mouseReleaseEvent = self._original_mouseReleaseEvent


def mousePressEvent(self, event):
    if self._active_button != QtCore.Qt.NoButton:
        return

    if (event.modifiers() & QtCore.Qt.CTRL) and event.button() == QtCore.Qt.LeftButton:
        self._active_button = QtCore.Qt.LeftButton
        self._use_zinc_mouse_event_handling = False
        point_on_plane = self._calculatePointOnPlane(event.x(), event.y())
        if point_on_plane is not None:
            self._model.setNodeLocation(point_on_plane)


def mouseMoveEvent(self, event):
    if (event.modifiers() & QtCore.Qt.CTRL) and self._active_button == QtCore.Qt.LeftButton:
        point_on_plane = self._calculatePointOnPlane(event.x(), event.y())
        if point_on_plane is not None:
            self._model.setNodeLocation(point_on_plane)


def mouseReleaseEvent(self, event):
    self._active_button = QtCore.Qt.NoButton


def _calculatePointOnPlane(self, x, y):
    from opencmiss.utils.maths.algorithms import calculateLinePlaneIntersection

    far_plane_point = self.unproject(x, -y, -1.0)
    near_plane_point = self.unproject(x, -y, 1.0)
    plane_point, plane_normal = self._model.getPlaneDescription()
    point_on_plane = calculateLinePlaneIntersection(near_plane_point, far_plane_point, plane_point, plane_normal)

    return point_on_plane


def rigid_transform_3D(A, B):
    assert len(A) == len(B)

    N = A.shape[1]  # total points
    centroid_A = np.mean(A, axis=1)
    centroid_B = np.mean(B, axis=1)

    # centre the points
    AA = A - np.tile(centroid_A, (1, N))
    BB = B - np.tile(centroid_B, (1, N))

    # dot is matrix multiplication for array
    H = AA * BB.T

    U, S, Vt = np.linalg.svd(H)

    R = Vt.T * U.T

    # special reflection case
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T * U.T

    t = -R * centroid_A + centroid_B

    return R, t

