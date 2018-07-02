

class Annotation(object):

    def __init__(self):
        self._data = {}

    def getLabels(self):
        labels = []
        for label_key in self._data:
            labels.append(label_key)
        return labels

    def getNode(self, label):
        return self._data[label]


class AnnotatedMesh3DHeartVentriclesWithBase1(Annotation):
    name = '3D Heart Ventricles with Base 1'

    def __init__(self):
        super(AnnotatedMesh3DHeartVentriclesWithBase1, self).__init__()
        self._data = {'LV apex': 46, 'RV apex': 112, 'LAD CFX junction': 40, 'RV wall extent': 118, }


class AnnotatedMesh3DHeartVentriclesWithBase2(Annotation):
    name = '3D Heart Ventricles with Base 2'

    def __init__(self):
        super(AnnotatedMesh3DHeartVentriclesWithBase2, self).__init__()
        self._data = {'LV apex': 62, 'RV apex': 167, 'LAD CFX junction': 54, 'RV wall extent': 191, }


def mkInst(cls, *args, **kwargs):
    try:
        return globals()[cls](*args, **kwargs)
    except:
        pass
        # print("Class %s is not defined" % cls)

    return None


class MeshAnnotationModel(object):

    def __init__(self):
        self._mesh_type = ''
        self._annotations = []

    def setMeshTypeByName(self, name):
        self._mesh_type = name

    def getNode(self, label):
        class_name = 'AnnotatedMesh{0}'.format(self._mesh_type.title().replace(' ', ''))
        annotation_class = mkInst(class_name)
        if annotation_class is not None:
            return annotation_class.getNode(label)

    def getFiducialMarkerLabels(self):
        class_name = 'AnnotatedMesh{0}'.format(self._mesh_type.title().replace(' ', ''))
        annotation_class = mkInst(class_name)
        if annotation_class is not None:
            return annotation_class.getLabels()

        return []

    def setMeshAnnotation(self, annotations):
        print('set annotation labels')
        self._annotations = annotations
        for annotation_group in annotations:
            annotation_group.addSubelements()
            print(annotation_group.getName())
            print(annotation_group.getLyphID())
            print(annotation_group.getFMANumber())

    def getAnnotationLabels(self):
        labels = []
        for annotation in self._annotations:
            labels.append((annotation.getName(), annotation.getFMANumber()))

        return labels

    def getAnnotationGroup(self, fmaTerm):
        for annotation in self._annotations:
            if fmaTerm == annotation.getFMANumber():
                return annotation.getGroup()

        return None
