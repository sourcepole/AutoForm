from qgis.core import QgsFeature,  QgsMapLayerRegistry
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from connector import Connector
from relationretriever import RelationRetriever

import psycopg2


class AutoForm:
    def __init__( self, iface ):
        self.iface = iface
        self.connector = Connector()
        self.relationretriever = RelationRetriever()

    def initGui(self):

        self.action = QAction("Generate Form", self.iface.mainWindow())
        self.iface.addPluginToMenu("AutoForm", self.action)
        QObject.connect(self.action, SIGNAL("activated()"), self.validateLayer)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu("AutoForm", self.action)

    def validateLayer(self):
        native_layer = self.iface.activeLayer()
        if native_layer:
            self.identifyRelations(native_layer)
            self.alterForm(native_layer)
            self.filterEmptyGroups()
            QMessageBox.information(self.iface.mainWindow(), "AutoForm", "Form widgets were successfully changed!")
        else:
            QMessageBox.warning(self.iface.mainWindow(), "Layer Error", "Please select a valid layer before running the plugin.")

    def alterForm(self, native_layer):
        field_index = 0
        for field in native_layer.pendingFields():
            f_type = field.typeName()
            if native_layer.editorWidgetV2(field_index) != 'TextEdit':
                pass
            elif f_type == "text":
                native_layer.setEditorWidgetV2(field_index, 'TextEdit')
                native_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
            elif f_type == "varchar":
                if field.length < 255:
                    native_layer.setEditorWidgetV2(field_index, 'TextEdit')
                    native_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                else:
                    native_layer.setEditorWidgetV2(field_index, 'TextEdit')
                    native_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': False, 'UseHtml': False})
            elif f_type == "date":
                native_layer.setEditorWidgetV2(field_index, 'DateTime')
                native_layer.setEditorWidgetV2Config(field_index, {'display_format': 'yyyy-MM-dd', 'field_format': 'yyyy-MM-dd', 'calendar_popup': True})
            elif f_type == "bool":
                native_layer.setEditorWidgetV2(field_index, 'CheckBox')
                native_layer.setEditorWidgetV2Config(field_index, {'CheckedState': 't', 'UncheckedState': 'f'})
            field_index += 1

    def handleValueRelations(self, new_layer, ref_native_col_num, ref_foreign_col_num, native_layer):
        fields = new_layer.pendingFields()
        foreign_column = fields[ref_foreign_col_num - 1].name()

        fields = native_layer.pendingFields()
        native_column = fields[ref_native_col_num - 1].name()

        if native_column and foreign_column:
            column_index = ref_native_col_num - 1
            new_layer_id = new_layer.id()
            native_layer.setEditorWidgetV2(column_index, 'ValueRelation')
            native_layer.setEditorWidgetV2Config(column_index, {'Layer': new_layer_id, 'Key': foreign_column, 'Value': foreign_column, "AllowMulti": False, "AllowNull": False, "OrderByValue": True})
            self.identifyRelations(new_layer)
            self.alterForm(new_layer)

    def identifyRelations(self, native_layer):
        data = native_layer.dataProvider()
        uri = QgsDataSourceURI(data.dataSourceUri())

        cur = self.connector.uriDatabaseConnect(uri)

        if cur is False:
            return
        else:
            self.relationretriever.setCur(cur)

        referenced_layers = self.relationretriever.retrieveReferencedTables(uri)

        self.handleLayers(cur, referenced_layers, uri, native_layer)

    def handleLayers(self, cur, referenced_layers, uri, native_layer):

        root = QgsProject.instance().layerTreeRoot()

        tableGroup = root.findGroup("Raw_data_tables")
        if not tableGroup:
            tableGroup = root.addGroup("Raw_data_tables")

        for a_layer in referenced_layers:
            self.relationretriever.setLayer(a_layer[0])
            foreign_tables = self.relationretriever.retrieveForeignTables()

            for a_table in foreign_tables:
                pkeyName = self.relationretriever.retrieveTablePrimaryKeyName()

                ref_foreign_col_num = self.relationretriever.retrieveForeignCol()
                ref_native_col_num = self.relationretriever.retrieveNativeCol()

                new_layer = self.addRefTables(uri, a_table[0], pkeyName, tableGroup)
                if new_layer is not False:
                    self.handleValueRelations(new_layer, ref_native_col_num, ref_foreign_col_num, native_layer)

    def addRefTables(self, uri, table, attr_name, tableGroup):
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
                QgsMapLayerRegistry.instance().addMapLayer(new_layer, False)
                tableGroup.addLayer(new_layer)
                return new_layer
            else:
                return False

    def filterEmptyGroups(self):
        root = QgsProject.instance().layerTreeRoot()
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                if not child.findLayers():
                    root.removeChildNode(child)
