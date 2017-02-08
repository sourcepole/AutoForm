from PyQt4.QtCore import *
from PyQt4.QtGui import *

import psycopg2


class Connector:
    def __init__(self):
        pass

    def uriDatabaseConnect(self, uri):
        layer_table = uri.table()
        layer_db = uri.database()
        layer_schema = uri.schema()
        layer_host = uri.host()
        layer_user = uri.username()
        layer_password = uri.password()
        layer_port = uri.port()

        try:
            conn_string = "dbname=%s user=%s host='%s' password=%s" % (layer_db, layer_user, layer_host, layer_password)
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
            return cur
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Connection Error", "Failed to connect to database. Please make sure that your connection information is correct.")
            return False
