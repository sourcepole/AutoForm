from PyQt4.QtCore import *
from PyQt4.QtGui import *

import psycopg2


class Connector:
    def __init__(self):
        pass

    def uriDatabaseConnect(self, uri):
        try:
            conn_string = "dbname=%s user=%s host='%s' password=%s" % (uri.database(), uri.username(), uri.host(), uri.password())
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
            return cur
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Connection Error", "Failed to connect to database. Please make sure that your connection information is correct.")
            return False
