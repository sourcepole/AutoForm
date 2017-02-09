# -*- coding: utf-8 -*-
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    copyright            : (C) 2017 by William Habelt / Sourcepole AG
#    email                : wha@sourcepole.ch


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
