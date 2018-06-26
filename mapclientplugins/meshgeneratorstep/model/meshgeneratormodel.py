"""
Created on 9 Mar, 2018 from mapclientplugins.meshgeneratorstep.

@author: Richard Christie
"""

import string

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.node import Node
from scaffoldmaker.scaffoldmaker import Scaffoldmaker
from scaffoldmaker.utils.zinc_utils import *
import numpy as np

from mapclientplugins.meshgeneratorstep.model.meshalignmentmodel import MeshAlignmentModel

STRING_FLOAT_FORMAT = '{:.8g}'


class MeshGeneratorModel(MeshAlignmentModel):
    """
    Framework for generating meshes of a number of types, with mesh type specific options
    """

    def __init__(self, region, material_module):
        super(MeshGeneratorModel, self).__init__()
        self._region_name = "generated_mesh"
        self._parent_region = region
        self._materialmodule = material_module
        self._region = None
        self._sceneChangeCallback = None
        self._deleteElementRanges = []
        self._scale = [ 1.0, 1.0, 1.0 ]
        self._settings = {
            'meshTypeName' : '',
            'meshTypeOptions' : { },
            'deleteElementRanges' : '',
            'scale' : '*'.join(STRING_FLOAT_FORMAT.format(value) for value in self._scale),
            'displayAxes' : True,
            'displayElementNumbers' : True,
            'displayLines' : True,
            'displayNodeDerivatives' : False,
            'displayNodeNumbers' : True,
            'displaySurfaces' : True,
            'displaySurfacesExterior' : True,
            'displaySurfacesTranslucent' : True,
            'displaySurfacesWireframe' : False,
            'displayXiAxes' : False
        }
        self._discoverAllMeshTypes()

    def _discoverAllMeshTypes(self):
        scaffoldmaker = Scaffoldmaker()
        self._meshTypes = scaffoldmaker.getMeshTypes()
        self._currentMeshType = scaffoldmaker.getDefaultMeshType()
        self._settings['meshTypeName'] = self._currentMeshType.getName()
        self._settings['meshTypeOptions'] = self._currentMeshType.getDefaultOptions()

    def getAllMeshTypeNames(self):
        meshTypeNames = []
        for meshType in self._meshTypes:
            meshTypeNames.append(meshType.getName())
        return meshTypeNames

    def getMeshTypeName(self):
        return self._settings['meshTypeName']

    def _getMeshTypeByName(self, name):
        for meshType in self._meshTypes:
            if meshType.getName() == name:
                return meshType
        return None

    def setMeshTypeByName(self, name):
        meshType = self._getMeshTypeByName(name)
        if meshType is not None:
            if meshType != self._currentMeshType:
                self._currentMeshType = meshType
                self._settings['meshTypeName'] = self._currentMeshType.getName()
                self._settings['meshTypeOptions'] = self._currentMeshType.getDefaultOptions()
                self._generateMesh()

    def getMeshTypeOrderedOptionNames(self):
        return self._currentMeshType.getOrderedOptionNames()

    def getMeshTypeOption(self, key):
        return self._settings['meshTypeOptions'][key]

    def setMeshTypeOption(self, key, value):
        oldValue = self._settings['meshTypeOptions'][key]
        # print('setMeshTypeOption: key ', key, ' value ', str(value))
        newValue = None
        try:
            if type(oldValue) is bool:
                newValue = bool(value)
            elif type(oldValue) is int:
                newValue = int(value)
            elif type(oldValue) is float:
                newValue = float(value)
            elif type(oldValue) is str:
                newValue = str(value)
            else:
                newValue = value
        except:
            print('setMeshTypeOption: Invalid value')
            return
        self._settings['meshTypeOptions'][key] = newValue
        self._currentMeshType.checkOptions(self._settings['meshTypeOptions'])
        # print('final value = ', self._settings['meshTypeOptions'][key])
        if self._settings['meshTypeOptions'][key] != oldValue:
            self._generateMesh()

    def getDeleteElementsRangesText(self):
        return self._settings['deleteElementRanges']

    def _parseDeleteElementsRangesText(self, elementRangesTextIn):
        """
        :return: True if ranges changed, otherwise False
        """
        elementRanges = []
        for elementRangeText in elementRangesTextIn.split(','):
            try:
                elementRangeEnds = elementRangeText.split('-')
                # remove trailing non-numeric characters, workaround for select 's' key ending up there
                for e in range(len(elementRangeEnds)):
                    size = len(elementRangeEnds[e])
                    for i in range(size):
                        if elementRangeEnds[e][size - i - 1] in string.digits:
                            break;
                    if i > 0:
                        elementRangeEnds[e] = elementRangeEnds[e][:(size - i)]
                elementRangeStart = int(elementRangeEnds[0])
                if len(elementRangeEnds) > 1:
                    elementRangeStop = int(elementRangeEnds[1])
                else:
                    elementRangeStop = elementRangeStart
                if elementRangeStop >= elementRangeStart:
                    elementRanges.append([elementRangeStart, elementRangeStop])
                else:
                    elementRanges.append([elementRangeStop, elementRangeStart])
            except:
                pass
        elementRanges.sort()
        elementRangesText = ''
        first = True
        for elementRange in elementRanges:
            if first:
                first = False
            else:
                elementRangesText += ','
            elementRangesText += str(elementRange[0])
            if elementRange[1] != elementRange[0]:
                elementRangesText += '-' + str(elementRange[1])
        changed = self._deleteElementRanges != elementRanges
        self._deleteElementRanges = elementRanges
        self._settings['deleteElementRanges'] = elementRangesText
        return changed

    def setDeleteElementsRangesText(self, elementRangesTextIn):
        if self._parseDeleteElementsRangesText(elementRangesTextIn):
            self._generateMesh()

    def getScaleText(self):
        return self._settings['scale']

    def createEEGPoints(self, region, eeg_group):
        fm = region.getFieldmodule()
        cache = fm.createFieldcache()
        coordinates = fm.findFieldByName('coordinates')
        coordinates = coordinates.castFiniteElement()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodeIdentifier = nodes.getSize() + 1


        #create EEG subset
        eeg_group.removeAllNodes()



        eeg_coord = [[1, 1, 1],
                     [1, .5, .5],
                     [0, .4, .4],
                     [1, .2, .2]]

        for i in range(len(eeg_coord)):
            eegNode = nodes.createNode(nodeIdentifier, nodetemplate)
            cache.setNode(eegNode)
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, eeg_coord[i])
            eeg_group.addNode(eegNode)
            nodeIdentifier += 1






    def createEEGSubField(self, region, coordinates):
        fm = region.getFieldmodule()
        cache = fm.createFieldcache()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodeIdentifier = nodes.getSize() + 1

        # create EEG subset
        field_group = fm.createFieldGroup()
        sub_set_field = field_group.createFieldNodeGroup(nodes)
        eeg_group = sub_set_field.getNodesetGroup()
        eeg_group.removeAllNodes()

        eeg_coord = [[1, 1, 1],
                     [1, .5, .5],
                     [0, .4, .4],
                     [1, .2, .2]]

        coordinates = coordinates.castFiniteElement()
        for i in range(len(eeg_coord)):
            eegNode = nodes.createNode(nodeIdentifier, nodetemplate)
            cache.setNode(eegNode)
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, eeg_coord[i])
            eeg_group.addNode(eegNode)
            nodeIdentifier += 1
        return eeg_group

    def _parseScaleText(self, scaleTextIn):
        """
        :return: True if scale changed, otherwise False
        """
        scale = []
        for valueText in scaleTextIn.split('*'):
            try:
                scale.append(float(valueText))
            except:
                scale.append(1.0)
        for i in range(3 - len(scale)):
            scale.append(scale[-1])
        if len(scale) > 3:
            scale = scale[:3]
        scaleText = '*'.join(STRING_FLOAT_FORMAT.format(value) for value in scale)
        changed = self._scale != scale
        self._scale = scale
        self._settings['scale'] = scaleText
        return changed

    def setScaleText(self, scaleTextIn):
        if self._parseScaleText(scaleTextIn):
            self._generateMesh()

    def registerSceneChangeCallback(self, sceneChangeCallback):
        self._sceneChangeCallback = sceneChangeCallback

    def _getVisibility(self, graphicsName):
        return self._settings[graphicsName]

    def _setVisibility(self, graphicsName, show):
        self._settings[graphicsName] = show
        graphics = self._region.getScene().findGraphicsByName(graphicsName)
        graphics.setVisibilityFlag(show)

    def isDisplayAxes(self):
        return self._getVisibility('displayAxes')

    def setDisplayAxes(self, show):
        self._setVisibility('displayAxes', show)

    def isDisplayElementNumbers(self):
        return self._getVisibility('displayElementNumbers')

    def setDisplayElementNumbers(self, show):
        self._setVisibility('displayElementNumbers', show)

    def isDisplayLines(self):
        return self._getVisibility('displayLines')

    def setDisplayLines(self, show):
        self._setVisibility('displayLines', show)

    def isDisplayNodeDerivatives(self):
        return self._getVisibility('displayNodeDerivatives')

    def setDisplayNodeDerivatives(self, show):
        graphicsName = 'displayNodeDerivatives'
        self._settings[graphicsName] = show
        scene = self._region.getScene()
        graphics = scene.getFirstGraphics()
        while graphics.isValid():
            if graphics.getName() == graphicsName:
                graphics.setVisibilityFlag(show)
            graphics = scene.getNextGraphics(graphics)

    def isDisplayNodeNumbers(self):
        return self._getVisibility('displayNodeNumbers')

    def setDisplayNodeNumbers(self, show):
        self._setVisibility('displayNodeNumbers', show)

    def isDisplaySurfaces(self):
        return self._getVisibility('displaySurfaces')

    def setDisplaySurfaces(self, show):
        self._setVisibility('displaySurfaces', show)

    def isDisplaySurfacesExterior(self):
        return self._settings['displaySurfacesExterior']

    def setDisplaySurfacesExterior(self, isExterior):
        self._settings['displaySurfacesExterior'] = isExterior
        surfaces = self._region.getScene().findGraphicsByName('displaySurfaces')
        surfaces.setExterior(self.isDisplaySurfacesExterior() if (self.getMeshDimension() == 3) else False)

    def isDisplaySurfacesTranslucent(self):
        return self._settings['displaySurfacesTranslucent']

    def setDisplaySurfacesTranslucent(self, isTranslucent):
        self._settings['displaySurfacesTranslucent'] = isTranslucent
        surfaces = self._region.getScene().findGraphicsByName('displaySurfaces')
        surfacesMaterial = self._materialmodule.findMaterialByName('trans_blue' if isTranslucent else 'solid_blue')
        surfaces.setMaterial(surfacesMaterial)

    def isDisplaySurfacesWireframe(self):
        return self._settings['displaySurfacesWireframe']

    def setDisplaySurfacesWireframe(self, isWireframe):
        self._settings['displaySurfacesWireframe'] = isWireframe
        surfaces = self._region.getScene().findGraphicsByName('displaySurfaces')
        surfaces.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_WIREFRAME if isWireframe else Graphics.RENDER_POLYGON_MODE_SHADED)

    def isDisplayXiAxes(self):
        return self._getVisibility('displayXiAxes')

    def setDisplayXiAxes(self, show):
        self._setVisibility('displayXiAxes', show)

    def needPerturbLines(self):
        """
        Return if solid surfaces are drawn with lines, requiring perturb lines to be activated.
        """
        if self._region is None:
            return False
        mesh2d = self._region.getFieldmodule().findMeshByDimension(2)
        if mesh2d.getSize() == 0:
            return False
        return self.isDisplayLines() and self.isDisplaySurfaces() and not self.isDisplaySurfacesTranslucent()

    def _getMesh(self):
        fm = self._region.getFieldmodule()
        for dimension in range(3,0,-1):
            mesh = fm.findMeshByDimension(dimension)
            if mesh.getSize() > 0:
                break
        if mesh.getSize() == 0:
            mesh = fm.findMeshByDimension(3)
        return mesh

    def getMeshDimension(self):
        return self._getMesh().getDimension()

    def getSettings(self):
        return self._settings

    def setSettings(self, settings):
        self._settings.update(settings)
        self._currentMeshType = self._getMeshTypeByName(self._settings['meshTypeName'])
        self._parseDeleteElementsRangesText(self._settings['deleteElementRanges'])
        # merge any new options for this generator
        savedMeshTypeOptions = self._settings['meshTypeOptions']
        self._settings['meshTypeOptions'] = self._currentMeshType.getDefaultOptions()
        self._settings['meshTypeOptions'].update(savedMeshTypeOptions)
        self._parseScaleText(self._settings['scale'])
        self._generateMesh()

    def _generateMesh(self):
        if self._region:
            self._parent_region.removeChild(self._region)
        self._region = self._parent_region.createChild(self._region_name)
        self._scene = self._region.getScene()
        fm = self._region.getFieldmodule()
        fm.beginChange()
        # logger = self._context.getLogger()
        annotationGroups = self._currentMeshType.generateMesh(self._region, self._settings['meshTypeOptions'])
        # loggerMessageCount = logger.getNumberOfMessages()
        # if loggerMessageCount > 0:
        #     for i in range(1, loggerMessageCount + 1):
        #         print(logger.getMessageTypeAtIndex(i), logger.getMessageTextAtIndex(i))
        #     logger.removeAllMessages()
        mesh = self._getMesh()
        # meshDimension = mesh.getDimension()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        if len(self._deleteElementRanges) > 0:
            deleteElementIdentifiers = []
            elementIter = mesh.createElementiterator()
            element = elementIter.next()
            while element.isValid():
                identifier = element.getIdentifier()
                for deleteElementRange in self._deleteElementRanges:
                    if (identifier >= deleteElementRange[0]) and (identifier <= deleteElementRange[1]):
                        deleteElementIdentifiers.append(identifier)
                element = elementIter.next()
            #print('delete elements ', deleteElementIdentifiers)
            for identifier in deleteElementIdentifiers:
                element = mesh.findElementByIdentifier(identifier)
                mesh.destroyElement(element)
            del element
            # destroy all orphaned nodes
            #size1 = nodes.getSize()
            nodes.destroyAllNodes()
            #size2 = nodes.getSize()
            #print('deleted', size1 - size2, 'nodes')
        fm.defineAllFaces()
        if annotationGroups is not None:
            for annotationGroup in annotationGroups:
                annotationGroup.addSubelements()
        if self._settings['scale'] != '1*1*1':
            coordinates = fm.findFieldByName('coordinates').castFiniteElement()
            scale = fm.createFieldConstant(self._scale)
            newCoordinates = fm.createFieldMultiply(coordinates, scale)
            fieldassignment = coordinates.createFieldassignment(newCoordinates)
            fieldassignment.assign()
            del newCoordinates
            del scale
        fm.endChange()
        self._createGraphics(self._region)
        if self._sceneChangeCallback is not None:
            self._sceneChangeCallback()

    def _createGraphics(self, region):
        # Node numbers are generated here
        fm = region.getFieldmodule()
        meshDimension = self.getMeshDimension()
        coordinates = fm.findFieldByName('coordinates')
        nodeDerivativeFields = [
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS1, 1),
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS2, 1),
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS3, 1)
        ]
        elementDerivativeFields = []
        for d in range(meshDimension):
            elementDerivativeFields.append(fm.createFieldDerivative(coordinates, d + 1))
        elementDerivativesField = fm.createFieldConcatenate(elementDerivativeFields)
        cmiss_number = fm.findFieldByName('cmiss_number')
        # make graphics
        scene = region.getScene()
        scene.beginChange()
        axes = scene.createGraphicsPoints()
        pointattr = axes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_XYZ)
        pointattr.setBaseSize([1.0,1.0,1.0])
        axes.setMaterial(self._materialmodule.findMaterialByName('grey50'))
        axes.setName('displayAxes')
        axes.setVisibilityFlag(self.isDisplayAxes())
        lines = scene.createGraphicsLines()
        lines.setCoordinateField(coordinates)
        lines.setName('displayLines')
        lines.setVisibilityFlag(self.isDisplayLines())


        nodeNumbers = scene.createGraphicsPoints()
        nodeNumbers.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodeNumbers.setCoordinateField(coordinates)
        pointattr = nodeNumbers.getGraphicspointattributes()
        pointattr.setLabelField(cmiss_number)



        ## EEG nodes
        nodeNumbers = scene.createGraphicsPoints()
        nodeNumbers.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodeNumbers.setCoordinateField(coordinates)


        fng = fm.createFieldNodeGroup(fm.findNodesetByName('nodes'))
        nodeNumbers.setSubgroupField(fng)
        ndg = fng.getNodesetGroup()
        self.createEEGPoints(region,ndg)

        pointattr = nodeNumbers.getGraphicspointattributes()
        pointattr.setLabelText(1, 'EEG Node')
        pointattr.setLabelOffset([.5, 0, 0])
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        pointattr.setBaseSize([.05, .05, .05])


        nodeNumbers.setMaterial(self._materialmodule.findMaterialByName('white'))
        nodeNumbers.setName('displayNodeNumbers')
        nodeNumbers.setVisibilityFlag(self.isDisplayNodeNumbers())


        elementNumbers = scene.createGraphicsPoints()
        elementNumbers.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        elementNumbers.setCoordinateField(coordinates)
        pointattr = elementNumbers.getGraphicspointattributes()
        pointattr.setLabelField(cmiss_number)
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
        elementNumbers.setMaterial(self._materialmodule.findMaterialByName('red'))
        elementNumbers.setName('displayElementNumbers')
        elementNumbers.setVisibilityFlag(self.isDisplayElementNumbers())
        surfaces = scene.createGraphicsSurfaces()
        surfaces.setCoordinateField(coordinates)
        surfaces.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_WIREFRAME if self.isDisplaySurfacesWireframe() else Graphics.RENDER_POLYGON_MODE_SHADED)
        surfaces.setExterior(self.isDisplaySurfacesExterior() if (meshDimension == 3) else False)
        surfacesMaterial = self._materialmodule.findMaterialByName('trans_blue' if self.isDisplaySurfacesTranslucent() else 'solid_blue')
        surfaces.setMaterial(surfacesMaterial)
        surfaces.setName('displaySurfaces')
        surfaces.setVisibilityFlag(self.isDisplaySurfaces())

        # derivative arrow width is based on shortest non-zero side
        minScale = 1.0
        first = True
        for i in range(coordinates.getNumberOfComponents()):
            absScale = abs(self._scale[i])
            if absScale > 0.0:
                if first or (absScale < minScale):
                    minScale = absScale
                    first = False
        width = 0.01*minScale

        nodeDerivativeMaterialNames = [ 'gold', 'silver', 'green' ]
        for i in range(meshDimension):
            nodeDerivatives = scene.createGraphicsPoints()
            nodeDerivatives.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodeDerivatives.setCoordinateField(coordinates)
            pointattr = nodeDerivatives.getGraphicspointattributes()
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_ARROW_SOLID)
            pointattr.setOrientationScaleField(nodeDerivativeFields[i])
            pointattr.setBaseSize([0.0, width, width])
            pointattr.setScaleFactors([1.0, 0.0, 0.0])
            nodeDerivatives.setMaterial(self._materialmodule.findMaterialByName(nodeDerivativeMaterialNames[i]))
            nodeDerivatives.setName('displayNodeDerivatives')
            nodeDerivatives.setVisibilityFlag(self.isDisplayNodeDerivatives())

        xiAxes = scene.createGraphicsPoints()
        xiAxes.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        xiAxes.setCoordinateField(coordinates)
        pointattr = xiAxes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_123)
        pointattr.setOrientationScaleField(elementDerivativesField)
        if meshDimension == 1:
            pointattr.setBaseSize([0.0, 2*width, 2*width])
            pointattr.setScaleFactors([0.25, 0.0, 0.0])
        elif meshDimension == 2:
            pointattr.setBaseSize([0.0, 0.0, 2*width])
            pointattr.setScaleFactors([0.25, 0.25, 0.0])
        else:
            pointattr.setBaseSize([0.0, 0.0, 0.0])
            pointattr.setScaleFactors([0.25, 0.25, 0.25])
        xiAxes.setMaterial(self._materialmodule.findMaterialByName('yellow'))
        xiAxes.setName('displayXiAxes')
        xiAxes.setVisibilityFlag(self.isDisplayXiAxes())

        # -----create Node for EEG starts here------ (pasted from scaffoldmaker)

        # -----create Node for EEG ends here------ (pasted from scaffoldmaker)

        self.applyAlignment()
        scene.endChange()


    def writeModel(self, file_name):
        self._region.writeFile(file_name)
