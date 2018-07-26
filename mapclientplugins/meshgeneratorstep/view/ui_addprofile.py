# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui\addprofile.ui'
#
# Created: Mon Jul  9 16:05:49 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_AddProfileDialog(object):
    def setupUi(self, AddProfileDialog):
        AddProfileDialog.setObjectName("AddProfileDialog")
        AddProfileDialog.resize(395, 195)
        self.verticalLayout = QtGui.QVBoxLayout(AddProfileDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame = QtGui.QFrame(AddProfileDialog)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.formLayout_2 = QtGui.QFormLayout(self.frame)
        self.formLayout_2.setObjectName("formLayout_2")
        self.profileName_label = QtGui.QLabel(self.frame)
        self.profileName_label.setObjectName("profileName_label")
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.profileName_label)
        self.profileName_lineEdit = QtGui.QLineEdit(self.frame)
        self.profileName_lineEdit.setObjectName("profileName_lineEdit")
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.profileName_lineEdit)
        self.apiToken_label = QtGui.QLabel(self.frame)
        self.apiToken_label.setObjectName("apiToken_label")
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.LabelRole, self.apiToken_label)
        self.apiToken_lineEdit = QtGui.QLineEdit(self.frame)
        self.apiToken_lineEdit.setObjectName("apiToken_lineEdit")
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.FieldRole, self.apiToken_lineEdit)
        self.apiSecret_label = QtGui.QLabel(self.frame)
        self.apiSecret_label.setObjectName("apiSecret_label")
        self.formLayout_2.setWidget(2, QtGui.QFormLayout.LabelRole, self.apiSecret_label)
        self.apiSecret_lineEdit = QtGui.QLineEdit(self.frame)
        self.apiSecret_lineEdit.setObjectName("apiSecret_lineEdit")
        self.formLayout_2.setWidget(2, QtGui.QFormLayout.FieldRole, self.apiSecret_lineEdit)
        self.verticalLayout.addWidget(self.frame)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(AddProfileDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(AddProfileDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), AddProfileDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), AddProfileDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(AddProfileDialog)

    def retranslateUi(self, AddProfileDialog):
        AddProfileDialog.setWindowTitle(QtGui.QApplication.translate("AddProfileDialog", "Add Profile", None, QtGui.QApplication.UnicodeUTF8))
        self.profileName_label.setText(QtGui.QApplication.translate("AddProfileDialog", "Profile name:", None, QtGui.QApplication.UnicodeUTF8))
        self.apiToken_label.setText(QtGui.QApplication.translate("AddProfileDialog", "API Token:", None, QtGui.QApplication.UnicodeUTF8))
        self.apiSecret_label.setText(QtGui.QApplication.translate("AddProfileDialog", "API Secret:", None, QtGui.QApplication.UnicodeUTF8))

