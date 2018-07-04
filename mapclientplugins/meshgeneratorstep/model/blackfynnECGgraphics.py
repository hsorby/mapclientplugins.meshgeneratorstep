"""
Created on 4th July, 2018 from mapclientplugins.meshgeneratorstep.

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


class EcgGraphics(object):
    """
    Framework for generating meshes of a number of types, with mesh type specific options
    """

    def __init__(self):
        pass

    def setRegion(self, region):
        self._region = region
        self._scene = self._region.getScene()
        self.numberInModel = 0

    def updateEEGcolours(self, value):
        fm = self._region.getFieldmodule()
        scene = self._region.getScene()
        displaySurface = scene.findGraphicsByName('displaySurfaces')
        constant = fm.createFieldConstant(value)
        displaySurface.setDataField(constant)


    def updateEEGnodeColours(self, values):
        fm = self._region.getFieldmodule()
        self._scene.beginChange()
        cache = fm.createFieldcache()
        colour = fm.findFieldByName('colour')
        colour = colour.castFiniteElement()
        nodeset = fm.findNodesetByName('nodes')
        for i in range(100):
            node = nodeset.findNodeByIdentifier(self.numberInModel+1+ (i % self.eegSize))
            cache.setNode(node)
            colour.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, values[(i % self.eegSize)])
        self._scene.endChange()

    def initialiseTimeSequences(self, data):
        fm = self._region.getFieldmodule()
        cache = fm.createFieldcache()
        colour = fm.findFieldByName('colour')


    def createEEGPoints(self, region, eeg_group, eeg_coord, i, cache):
        # createEEGPoints creates subgroups of points that use the 'colour' field to change colour

        fm = region.getFieldmodule()
        coordinates = fm.findFieldByName('coordinates')
        coordinates = coordinates.castFiniteElement()
        colour = fm.findFieldByName('colour')
        colour = colour.castFiniteElement()

        # Create templates
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.defineField(colour)
        nodetemplate.setValueNumberOfVersions(colour, -1, Node.VALUE_LABEL_VALUE, 1)

        # Assign values for the new EEG subset
        eeg_group.removeAllNodes()
        eegNode = nodes.createNode(self.numberInModel + i + 1, nodetemplate)
        cache.setNode(eegNode)
        coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, eeg_coord[i])
        cache.setTime(0)
        cache.setNode(eegNode)
        colour.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, .1)
        cache.clearLocation()
        cache.setTime(1)
        cache.setNode(eegNode)
        colour.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, .9)
        eeg_group.addNode(eegNode)

    def createGraphics(self):
        # Node numbers are generated here
        fm = self._region.getFieldmodule()
        # make graphics
        scene = self._region.getScene()
        scene.beginChange()
        coordinates = fm.findFieldByName('coordinates')

        # Add EEG nodes
        #eeg_coord = eegModel.get_all_coordinates()

        grid_size = 1
        elements_on_side = 10

        eeg_coord = []

        for i in range(elements_on_side):
            for j in range(elements_on_side):
                eeg_coord.append([i*grid_size/elements_on_side, j*grid_size/elements_on_side, 0])

        self.eegSize = len(eeg_coord)

        # Add Spectrum
        spcmod = scene.getSpectrummodule()
        spec = spcmod.getDefaultSpectrum()
        spec.setName('eegColourSpectrum')

        cache = fm.createFieldcache()

        # Initialise all subgroup parameters
        self.ndsg = []  # (node set group)
        self.pointattrList = []
        self.spectrumList = []
        self.nodeColours = []
        finite_element_field = []
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        self.numberInModel = 8

        #create all EEG subgroups
        colour = fm.createFieldFiniteElement(1)
        colour.setName('colour')
        colour.setManaged(True)
        for i in range(len(eeg_coord)):
            #create new graphics for our subgroup
            self.nodeColours.append(scene.createGraphicsPoints())
            self.nodeColours[i].setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            self.nodeColours[i].setCoordinateField(coordinates)

            # create new subgroup containing our node
            fng = fm.createFieldNodeGroup(fm.findNodesetByName('nodes'))
            self.ndsg.append(fng.getNodesetGroup())
            self.createEEGPoints(self._region, self.ndsg[i], eeg_coord, i, cache)
            self.nodeColours[i].setSubgroupField(fng)

            #set attributes for our new node
            self.nodeColours[i].setSpectrum(spec)
            self.nodeColours[i].setDataField(colour)
            self.pointattrList.append(self.nodeColours[i].getGraphicspointattributes())
            self.pointattrList[i].setLabelText(1, f'ECG Node {i}')
            self.pointattrList[i].setLabelOffset([1.5, 1.5, 0])
            self.pointattrList[i].setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
            self.pointattrList[i].setBaseSize([.05, .05, 2])

        scene.endChange()
