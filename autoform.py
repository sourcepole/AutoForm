from qgis.core import QgsFeature,  QgsMapLayerRegistry
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

import psycopg2
import os


class AutoForm:
    def __init__( self, iface ):
        self.iface = iface

    def initGui(self):

        self.action = QAction("Generate Form", self.iface.mainWindow())
        self.iface.addPluginToMenu("AutoForm", self.action)
        QObject.connect(self.action, SIGNAL("activated()"), self.validateLayer)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu("AutoForm", self.action)

    def validateLayer(self):
        layer = self.iface.activeLayer()
        if layer:
            self.identifyRelations(layer)
            field_index = 0
            for field in layer.pendingFields():
                f_type = field.typeName()
                if layer.editorWidgetV2(field_index) != 'TextEdit':
                    pass
                elif f_type == "text":
                    layer.setEditorWidgetV2(field_index, 'TextEdit')
                    layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                elif f_type == "varchar":
                    if field.length < 255:
                        layer.setEditorWidgetV2(field_index, 'TextEdit')
                        layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                    else:
                        layer.setEditorWidgetV2(field_index, 'TextEdit')
                        layer.setEditorWidgetV2Config(field_index, {'IsMultiline': False, 'UseHtml': False})
                elif f_type == "date":
                    layer.setEditorWidgetV2(field_index, 'DateTime')
                    layer.setEditorWidgetV2Config(field_index, {'display_format': 'yyyy-MM-dd', 'field_format': 'yyyy-MM-dd', 'calendar_popup': True})
                elif f_type == "bool":
                    layer.setEditorWidgetV2(field_index, 'CheckBox')
                    layer.setEditorWidgetV2Config(field_index, {'CheckedState': 't', 'UncheckedState': 'f'})
                field_index += 1
        else:
            QMessageBox.warning(self.iface.mainWindow(), "Layer Error", "Please select a valid layer before running the plugin.")

    def identifyRelations(self, layer):
        data = layer.dataProvider()
        uri = QgsDataSourceURI(data.dataSourceUri())

        cur = self.uridbconnect(uri)

        if cur is False:
            return

        oid_query = "SELECT oid FROM pg_class WHERE relname='%s'" % uri.table()
        cur.execute(oid_query)
        layer_oid = cur.fetchone()

        fk_query = "SELECT confrelid FROM pg_constraint WHERE conrelid='%s' AND contype = 'f'" % layer_oid
        cur.execute(fk_query)
        referenced_layers = cur.fetchall()

        self.handlelayers(cur, referenced_layers, uri, layer)

    def handlelayers(self, cur, referenced_layers, uri, layer):
        for a_layer in referenced_layers:
            ftable_query = "SELECT relname FROM pg_class WHERE oid='%s'" % a_layer[0]
            cur.execute(ftable_query)
            foreign_tables = cur.fetchall()
            for a_table in foreign_tables:
                pkey_query_1 = "SELECT conkey FROM pg_constraint WHERE conrelid = '%s' AND contype = 'p'" % a_layer[0]
                cur.execute(pkey_query_1)
                pkey_column = cur.fetchall()
                for column in pkey_column:
                    column[0][0]

                pkey_query_2 = "SELECT attname FROM pg_attribute WHERE attrelid='%s' AND attnum = '%s'" % (a_layer[0], column[0][0])
                cur.execute(pkey_query_2)
                att_names = cur.fetchall()
                for att_name in att_names:
                    att_name[0]

                ref_foreign_col_num = self.retrieveforeigncol(cur, a_layer[0])
                ref_native_col_num = self.retrievenativecol(cur, a_layer[0])

                new_layer = self.addreftables(uri, a_table[0], att_name[0])
                if new_layer is not False:
                    fields = new_layer.pendingFields()
                    foreign_column = fields[ref_foreign_col_num - 1].name()

                    fields = layer.pendingFields()
                    native_column = fields[ref_native_col_num - 1].name()

                    if native_column and foreign_column:
                        column_index = ref_native_col_num - 1
                        new_layer_id = new_layer.id()
                        layer.setEditorWidgetV2(column_index, 'ValueRelation')
                        layer.setEditorWidgetV2Config(column_index, {'Layer': new_layer_id, 'Key': foreign_column, 'Value': foreign_column, "AllowMulti": False, "AllowNull": False, "OrderByValue": True})

    def uridbconnect(self, uri):

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

    def addreftables(self, uri, table, attr_name):
        foreign_uri = QgsDataSourceURI()
        foreign_uri.setConnection(uri.host(), uri.port(), uri.database(), uri.username(), uri.password())
        foreign_uri.setDataSource(uri.schema(), table, None, "", attr_name)
        new_layer = QgsVectorLayer(foreign_uri.uri(), table, "postgres")
        if new_layer.isValid:
            layer_exists = False

            for layers in QgsMapLayerRegistry.instance().mapLayers().values():
                layer_data = layers.dataProvider()
                if foreign_uri.uri() == layer_data.dataSourceUri():
                    layer_exists = True

            if not layer_exists:
                QgsMapLayerRegistry.instance().addMapLayer(new_layer)
                return new_layer
            else:
                return False

    def retrieveforeigncol(self, cur, layer):
        fkey_query = "SELECT confkey FROM pg_constraint WHERE confrelid = %s AND contype = 'f'" % layer
        cur.execute(fkey_query)
        fkey_column = cur.fetchall()
        for column in fkey_column:
            ref_foreign_col_num = column[0][0]

        return ref_foreign_col_num

    def retrievenativecol(self, cur, layer):
        nfield_query = "SELECT conkey FROM pg_constraint WHERE confrelid = %s AND contype = 'f'" % layer
        cur.execute(nfield_query)
        nfield_column = cur.fetchall()
        for column in nfield_column:
            ref_native_col_num = column[0][0]

        return ref_native_col_num
