

from PySide import QtCore, QtGui

from blackfynn import Blackfynn
from blackfynn.base import UnauthorizedException
from mapclientplugins.meshgeneratorstep.view.ui_addprofile import Ui_AddProfileDialog
from mapclient.view.utils import set_wait_cursor


class AddProfileDialog(QtGui.QDialog):

    def __init__(self, parent, existing_profile_names):
        super(AddProfileDialog, self).__init__(parent)
        self._ui = Ui_AddProfileDialog()
        self._ui.setupUi(self)
        self._existing_profile_names = existing_profile_names

        self._delay_timer = QtCore.QTimer()
        self._delay_timer.setSingleShot(True)
        self._delay_timer.setInterval(750)

        self._update_ui()
        self._make_connections()

    def _update_ui(self, good_profile=False):
        not_existing_name = self._ui.profileName_lineEdit.text() not in self._existing_profile_names

        ok_button = self._ui.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        ok_button.setEnabled(not_existing_name and good_profile)

    def _make_connections(self):
        self._ui.profileName_lineEdit.textEdited.connect(self._delay_profile_test)
        self._ui.apiToken_lineEdit.textEdited.connect(self._delay_profile_test)
        self._ui.apiSecret_lineEdit.textEdited.connect(self._delay_profile_test)
        self._delay_timer.timeout.connect(self._test_profile)

    @set_wait_cursor
    def _can_access_blackfynn(self, api_key, api_secret):
        can_access = False
        bf = Blackfynn(api_token=api_key, api_secret=api_secret)
        if bf.context.exists:
            can_access = True

        return can_access

    def _delay_profile_test(self):
        self._delay_timer.stop()
        self._delay_timer.start()

    def _test_profile(self):
        success = False
        len_profile_good = len(self._ui.profileName_lineEdit.text()) > 0
        api_key = self._ui.apiToken_lineEdit.text().strip()
        api_secret = self._ui.apiSecret_lineEdit.text().strip()
        len_token_good = len(api_key) == 36
        len_secret_good = len(api_secret) == 36
        if len_token_good and len_secret_good and len_profile_good:
            try:
                success = self._can_access_blackfynn(api_key, api_secret)
            except UnauthorizedException:
                QtGui.QMessageBox.critical(self, 'Unauthorized token set',
                                           'The token set is not authorized to access the blackfynn platform.')

            if not success:
                QtGui.QMessageBox.critical(self, 'Unknown error',
                                           'An unknown error has occured whilst attempting to '
                                           'contact the blackfynn platfrom.')

        self._update_ui(success)

    def profile(self):
        p = {'name': self._ui.profileName_lineEdit.text(),
             'token': self._ui.apiToken_lineEdit.text().strip(),
             'secret': self._ui.apiSecret_lineEdit.text().strip(),}
        return p
