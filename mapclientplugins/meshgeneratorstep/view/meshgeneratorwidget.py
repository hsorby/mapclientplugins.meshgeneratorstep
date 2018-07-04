"""
Created on Aug 29, 2017

@author: Richard Christie
"""

import types
from PySide import QtGui, QtCore
from functools import partial
# imports added for pop up graph
import pyqtgraph as pg
import numpy as np

from mapclientplugins.meshgeneratorstep.model.blackfynnmodel import BlackfynnModel
from mapclientplugins.meshgeneratorstep.model.fiducialmarkermodel import FIDUCIAL_MARKER_LABELS
from mapclientplugins.meshgeneratorstep.view.ui_meshgeneratorwidget import Ui_MeshGeneratorWidget

from opencmiss.utils.maths import vectorops


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
        self._ui.sceneviewer_widget.setContext(model.getContext())
        self._ui.sceneviewer_widget.setModel(self._plane_model)
        self._model.registerSceneChangeCallback(self._sceneChanged)
        self._doneCallback = None
        self._populateFiducialMarkersComboBox()
        self._marker_mode_active = False
        self._have_images = False
        self.x = 0
        self.y = 0
        # self._populateAnnotationTree()
        meshTypeNames = self._generator_model.getAllMeshTypeNames()
        for meshTypeName in meshTypeNames:
            self._ui.meshType_comboBox.addItem(meshTypeName)
        self._makeConnections()

        self._blackfynn = BlackfynnModel()

        # All this needs to go.
        self._ui.sceneviewer_widget.pw = None
        self._ui.sceneviewer_widget.data = {}
        self._y_scaled = 0
        self._pw = None
        self._time = 0
        self._data = None

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

    def _sceneAnimate(self):
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            self._model.loadSettings()
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            self._autoPerturbLines()
            self._viewAll()


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

        # self._ui.submitButton.clicked.connect(self._submitClicked)
        # self._ui.displayEEGAnimation_checkBox.clicked.connect(self._EEGAnimationClicked)
        # self._ui.treeWidgetAnnotation.itemSelectionChanged.connect(self._annotationSelectionChanged)
        # self._ui.treeWidgetAnnotation.itemChanged.connect(self._annotationItemChanged)

        # currently not able to loop it (will have to do later
        # self._ui.LG3.clicked.connect(self._lg3)
        # self._ui.LG4.clicked.connect(self._lg4)
        # self._ui.LG10.clicked.connect(self._lg10)
        # self._ui.LG3.setText('')
        # self._ui.LG3.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
        # self._ui.LG4.setText('')
        # self._ui.LG4.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
        # self._ui.LG10.setText('')
        # self._ui.LG10.setStyleSheet("background-color: rgba(255, 255, 255, 0);")

    def _fiducialMarkerChanged(self):
        self._fiducial_marker_model.setActiveMarker(self._ui.fiducialMarker_comboBox.currentText())

    def _displayFiducialMarkersClicked(self):
        self._fiducial_marker_model.setDisplayFiducialMarkers(self._ui.displayFiducialMarkers_checkBox.isChecked())

    def _populateFiducialMarkersComboBox(self):
        self._ui.fiducialMarker_comboBox.addItems(FIDUCIAL_MARKER_LABELS)

    def _createFMAItem(self, parent, text, fma_id):
        item = QtGui.QTreeWidgetItem(parent)
        item.setText(0, text)
        item.setData(0, QtCore.Qt.UserRole + 1, fma_id)
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
            if self._pw is not None:
                self.line.setValue(round(value, 3)) # adjust time marker
            if self._ui.displayEEGAnimation_checkBox.isChecked() and self._y_scaled.any() is not 0:
                # Use model to update colours
                self._generator_model.updateEEGcolours(self._y_scaled[self._currentFrame(value)])
        self._ui.timeValue_doubleSpinBox.blockSignals(False)


    def _EEGAnimationClicked(self):
        if self._data:
            # scale the data
            numFrames = self._plane_model.getFrameCount()
            y = np.array(self._data['y'])
            yt = np.add(y, np.amin(y) * -1)
            x = np.linspace(0, 1, len(yt))
            xterp = np.linspace(0, 1, numFrames)
            yterp = np.interp(xterp, x, yt)
            y_scaled = np.multiply(yterp, 1 / np.amax(yterp))
            self._y_scaled = y_scaled

    def _currentFrame(self, value):
        frame_count = self._plane_model.getFrameCount()
        frame_values = np.linspace(0, 4, frame_count)
        current_frame = (np.abs(frame_values - value)).argmin()
        return current_frame

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

    def _submitClicked(self):
    # submitClicked initialises all the blackfynn functionality and updates login fields.
        if self._ui.api_key.displayText() != 'API Key' and self._ui.api_secret.text() != '***************************':
            self._ui.Login_groupBox.setTitle(QtGui.QApplication.translate("MeshGeneratorWidget", "Login details saved, click on a node to open graphs", None,
                                                                       QtGui.QApplication.UnicodeUTF8))
            # self._ui.sceneviewer_widget.blackfynn.api_token = self._ui.api_key.text()
            # self._ui.sceneviewer_widget.blackfynn.api_secret = self._ui.api_secret.text()
            self.initialiseBlackfynnData()
            self._ui.api_secret.setText('***************************')

            # self._ui.sceneviewer_widget.blackfynn.set_params(channels='LG4', window_from_start=4)
            # self._ui.sceneviewer_widget.blackfynn.set_api_key_login()
            # self._ui.sceneviewer_widget.data = self._ui.sceneviewer_widget.blackfynn.get()
            self.blackfynn.loaded = True

            # need to add the blackfynn data initialisation here

    def initialiseBlackfynnData(self):
        # self.blackfynn.api_key = self._ui.api_key.text()  <- commented so that we do not have to enter key each time
        # self.blackfynn.api_secret = self._ui.api_secret.text()
        self.blackfynn.set_api_key_login()
        self.blackfynn.set_params(channels='LG4', window_from_start=4) # need to add dataset selection
        self._data = self.blackfynn.get()
        self._pw = pg.plot()
        self.updatePlot(4)

    def updatePlot(self, key):
        try:
            self._data['cache'][f'LG{key}']
        except KeyError:
            print('ERROR: selected data could not be found')
            self._pw.plot(title='Error in data collection')
            return
        self._pw.clear()
        self._pw.plot(self._data['x'],
                      self._data['cache'][f'LG{key}'],
                      pen='b',
                      title=f'EEG values from {key} (LG{key})',
                      labels={'left': f'EEG value of node LG{key}', 'bottom': 'time in seconds'})
        self.line = self._pw.addLine(x=self._model.getCurrentTime(), pen='r')  # show current time

    # For linking each EEG node
    def _lg3(self):
        self.updatePlot(3)

    def _lg4(self):
        self.updatePlot(4)

    def _lg10(self):
        self.updatePlot(10)

    def EEGSelectionDisplay(self, key):
        # For selecting EEG (brain) points
        print(f'key {key} clicked!')
        if self._data:
            self._pw.clear()
            self._pw.plot(self._data['x'], self._data['cache'][f'LG{key}'], pen='b', title=f'EEG values from {key} (LG{key})',
                          labels={'left': f'EEG value of node LG{key}', 'bottom': 'time in seconds'})
            self.line = self._pw.addLine(x=self._model.getCurrentTime(), pen='r')  # show current time

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
        print(item.text(0))
        print(item.data(0, QtCore.Qt.UserRole + 1))

    def _viewAll(self):
        """
        Ask sceneviewer to show all of scene.
        """
        if self._ui.sceneviewer_widget.getSceneviewer() is not None:
            self._ui.sceneviewer_widget.viewAll()

    def keyPressEvent(self, event):
        if event.modifiers() & QtCore.Qt.CTRL and QtGui.QApplication.mouseButtons() == QtCore.Qt.NoButton:
            self._marker_mode_active = True
            self._ui.sceneviewer_widget._model = self._fiducial_marker_model
            self._original_mousePressEvent = self._ui.sceneviewer_widget.mousePressEvent
            self._ui.sceneviewer_widget.original_mousePressEvent = self._ui.sceneviewer_widget.mousePressEvent
            self._ui.sceneviewer_widget.plane_model_temp = self._plane_model

            self._ui.sceneviewer_widget._calculatePointOnPlane = types.MethodType(_calculatePointOnPlane, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mousePressEvent = types.MethodType(mousePressEvent, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.foundNode = False
            self._model.printLog()


    def keyReleaseEvent(self, event):
        if self._marker_mode_active:
            self._marker_mode_active = False
            self._ui.sceneviewer_widget._model = self._plane_model
            self._ui.sceneviewer_widget._calculatePointOnPlane = None
            self._ui.sceneviewer_widget.mousePressEvent = self._original_mousePressEvent
            if self._ui.sceneviewer_widget.foundNode == True:
                self.updatePlot(self._ui.sceneviewer_widget.nodeKey)


def mousePressEvent(self, event):
    if self._active_button != QtCore.Qt.NoButton:
        return

    if (event.modifiers() & QtCore.Qt.CTRL) and event.button() == QtCore.Qt.LeftButton:
        point_on_plane = self._calculatePointOnPlane(event.x(), event.y())
        print('Location of click (x,y): (' + str(event.x()) + ', ' + str(event.y()) +')')
        node = self.getNearestNode(event.x(), event.y())
        if node.isValid():
            self.foundNode = True
            self.nodeKey = node.getIdentifier()

        # return sceneviewers 'mouspressevent' function to its version for navigation

        self._model = self.plane_model_temp
        self._calculatePointOnPlane = None
        self.mousePressEvent = self.original_mousePressEvent
    return [event.x(), event.y()]


def _calculatePointOnPlane(self, x, y):
    from opencmiss.utils.maths.algorithms import calculateLinePlaneIntersection

    far_plane_point = self.unproject(x, -y, -1.0)
    near_plane_point = self.unproject(x, -y, 1.0)
    plane_point, plane_normal = self._model.getPlaneDescription()
    point_on_plane = calculateLinePlaneIntersection(near_plane_point, far_plane_point, plane_point, plane_normal)
    #print(point_on_plane)
    return point_on_plane


