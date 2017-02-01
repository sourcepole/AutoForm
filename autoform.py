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
        QObject.connect(self.action, SIGNAL("activated()"), self.validateLayer)
        self.iface.addPluginToMenu("AutoForm", self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu("AutoForm", self.action)

    def validateLayer(self):
        layer = self.iface.activeLayer()
        if layer:
            features = layer.getFeatures()
            self.identifyRelations(layer)
            for feature in features:
                field_index = 0
                for field in feature.fields():
                    f_type = field.typeName()
                    if layer.editorWidgetV2(field_index) != 'TextEdit':
                        break
                    if f_type == "text":
                        layer.setEditorWidgetV2(field_index, 'TextEdit')
                        layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                    if f_type == "varchar":
                        if field.length > 255:
                            layer.setEditorWidgetV2(field_index, 'TextEdit')
                            layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                        else:
                            layer.setEditorWidgetV2(field_index, 'TextEdit')
                            layer.setEditorWidgetV2Config(field_index, {'IsMultiline': False, 'UseHtml': False})
                    if f_type == "date":
                        layer.setEditorWidgetV2(field_index, 'DateTime')
                        layer.setEditorWidgetV2Config(field_index, {'display_format': 'yyyy-MM-dd', 'field_format': 'yyyy-MM-dd', 'calendar_popup': True})
                    if f_type == "bool":
                        layer.setEditorWidgetV2(field_index, 'CheckBox')
                        layer.setEditorWidgetV2Config(field_index, {'CheckedState': 't', 'UncheckedState': 'f'})
                    if f_type == "int8":
                        pass
                    if f_type == "int4":
                        pass
                    field_index += 1
        else:
            print "Please select a Layer"

    def identifyRelations(self, layer):
        print QgsProject.instance().relationManager().referencedRelations(layer)
        self.host = os.environ.get('PGHOST')
        self.port = os.environ.get('PGPORT')
        username = os.environ.get('PGUSER')
        password = os.environ.get('PGPASSWORD')
        self.dbname = os.environ.get('PGDATABASE')



        print "Connection achieved!"
        data = layer.dataProvider()
        print data.dataSourceUri()
        uri = QgsDataSourceURI(data.dataSourceUri())
        print uri.host()

        layer_table = uri.table()
        layer_db = uri.database()
        layer_schema = uri.schema()
        layer_host = uri.host()
        layer_user = uri.username()
        layer_password = uri.password()

        try:
            conn_string = "dbname=%s user=%s host='localhost' password=%s" % (layer_db, layer_user, layer_password)
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
        except:
            print "Connection Error"
            return

        oid_query = "SELECT oid FROM pg_class WHERE relname='%s'" % layer_table
        cur.execute(oid_query)
        layer_oid = cur.fetchone()

        fk_query = "SELECT confrelid FROM pg_constraint WHERE conrelid='%s' AND contype = 'f'" % layer_oid
        cur.execute(fk_query)
        referenced_layers = cur.fetchall()

        for a_layer in referenced_layers:
            ftable_query = "SELECT relname FROM pg_class WHERE oid='%s'" % a_layer[0]
            cur.execute(ftable_query)
            foreign_tables = cur.fetchall()
            for a_table in foreign_tables:
                print a_table[0]
                print a_layer[0]

                pkey_query_1 = "SELECT conkey FROM pg_constraint WHERE conrelid = '%s' AND contype = 'p'" % a_layer[0]
                cur.execute(pkey_query_1)
                pkey_column = cur.fetchall()
                for column in pkey_column:
                    print column[0][0]

                pkey_query_2 = "SELECT attname FROM pg_attribute WHERE attrelid='%s' AND attnum = '%s'" % (a_layer[0], column[0][0])
                cur.execute(pkey_query_2)
                att_names = cur.fetchall()
                for att_name in att_names:
                    print att_name[0]

                fkey_query = "SELECT confkey FROM pg_constraint WHERE confrelid = %s AND contype = 'f'" % a_layer[0]
                cur.execute(fkey_query)
                fkey_column = cur.fetchall()
                for column in fkey_column:
                    ref_foreign_col_num = column[0][0]

                nfield_query = "SELECT conkey FROM pg_constraint WHERE confrelid = %s AND contype = 'f'" % a_layer[0]
                cur.execute(nfield_query)
                nfield_column = cur.fetchall()
                for column in nfield_column:
                    ref_native_col_num = column[0][0]

                foreign_uri = QgsDataSourceURI()
                foreign_uri.setConnection("localhost", "5432", layer_db, "wha", "HtVlUUDNis1AMQRf5ZY9HtVlUUDNis1AMQRf5ZY9")
                foreign_uri.setDataSource(layer_schema, a_table[0], None, "", att_name[0])
                print foreign_uri
                new_layer = QgsVectorLayer(foreign_uri.uri(), a_table[0], "postgres")
                if new_layer.isValid:
                    layer_exists = False

                    for layers in QgsMapLayerRegistry.instance().mapLayers().values():
                        layer_data = layers.dataProvider()
                        if foreign_uri.uri() == layer_data.dataSourceUri():
                            layer_exists = True

                    if not layer_exists:
                        QgsMapLayerRegistry.instance().addMapLayer(new_layer)

                    fields = new_layer.pendingFields()
                    foreign_column = fields[ref_foreign_col_num - 1].name()

                    fields = layer.pendingFields()
                    native_column = fields[ref_native_col_num - 1].name()

                    if native_column and foreign_column:
                        column_index = ref_native_col_num - 1

                        layer.setEditorWidgetV2(column_index, 'ValueRelation')
                        layer.setEditorWidgetV2Config(column_index, {'Layer': new_layer.id(), 'Key': foreign_column, 'Value': foreign_column})
