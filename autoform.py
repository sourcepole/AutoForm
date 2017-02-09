# -*- coding: utf-8 -*-
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    copyright            : (C) 2017 by William Habelt / Sourcepole AG
#    email                : wha@sourcepole.ch


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

    def initGui(self):

        self.action = QAction("Generate Form", self.iface.mainWindow())
        self.iface.addPluginToMenu("AutoForm", self.action)
        QObject.connect(self.action, SIGNAL("activated()"), self.handleFormofLayer)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu("AutoForm", self.action)

    def handleFormofLayer(self):
        selected_layer = self.iface.activeLayer()
        if selected_layer:
            self.identifyRelations(selected_layer)
            self.alterForm(selected_layer)
            self.filterEmptyGroups()
            QMessageBox.information(self.iface.mainWindow(), "AutoForm", "Form widgets were successfully changed!")
        else:
            QMessageBox.warning(self.iface.mainWindow(), "Layer Error", "Please select a valid layer before running the plugin.")

    def alterForm(self, selected_layer):
        field_index = 0
        for field in selected_layer.pendingFields():
            f_type = field.typeName()
            if selected_layer.editorWidgetV2(field_index) != 'TextEdit':
                pass
            elif f_type == "text":
                selected_layer.setEditorWidgetV2(field_index, 'TextEdit')
                selected_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
            elif f_type == "varchar":
                if field.length < 255:
                    selected_layer.setEditorWidgetV2(field_index, 'TextEdit')
                    selected_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': True, 'UseHtml': False})
                else:
                    selected_layer.setEditorWidgetV2(field_index, 'TextEdit')
                    selected_layer.setEditorWidgetV2Config(field_index, {'IsMultiline': False, 'UseHtml': False})
            elif f_type == "date":
                selected_layer.setEditorWidgetV2(field_index, 'DateTime')
                selected_layer.setEditorWidgetV2Config(field_index, {'display_format': 'yyyy-MM-dd', 'field_format': 'yyyy-MM-dd', 'calendar_popup': True})
            elif f_type == "bool":
                selected_layer.setEditorWidgetV2(field_index, 'CheckBox')
                selected_layer.setEditorWidgetV2Config(field_index, {'CheckedState': 't', 'UncheckedState': 'f'})
            field_index += 1

    def handleValueRelations(self, new_layer, ref_native_col_num, ref_foreign_col_num, selected_layer):
        fields = new_layer.pendingFields()
        foreign_column = fields[ref_foreign_col_num - 1].name()

        fields = selected_layer.pendingFields()
        native_column = fields[ref_native_col_num - 1].name()

        if native_column and foreign_column:
            column_index = ref_native_col_num - 1
            new_layer_id = new_layer.id()
            selected_layer.setEditorWidgetV2(column_index, 'ValueRelation')
            selected_layer.setEditorWidgetV2Config(column_index, {'Layer': new_layer_id, 'Key': foreign_column, 'Value': foreign_column, "AllowMulti": False, "AllowNull": False, "OrderByValue": True})
            self.identifyRelations(new_layer)
            self.alterForm(new_layer)

    def identifyRelations(self, selected_layer):
        data = selected_layer.dataProvider()
        uri = QgsDataSourceURI(data.dataSourceUri())

        cur = self.connector.uriDatabaseConnect(uri)

        if cur is False:
            return

        self.handleLayers(cur, uri, selected_layer)

    def handleLayers(self, cur, uri, selected_layer):

        relationretriever = RelationRetriever(cur)
        referenced_layers = relationretriever.retrieveReferencedTables(uri)

        root = QgsProject.instance().layerTreeRoot()
        tableGroup = root.findGroup("Raw_data_tables")
        if not tableGroup:
            tableGroup = root.addGroup("Raw_data_tables")

        for a_layer in referenced_layers:
            relationretriever.setLayer(a_layer[0])
            foreign_tables = relationretriever.retrieveForeignTables()

            for a_table in foreign_tables:
                pkeyName = relationretriever.retrieveTablePrimaryKeyName()

                ref_foreign_col_num = relationretriever.retrieveForeignCol()
                ref_native_col_num = relationretriever.retrieveNativeCol()

                new_layer = self.addRefTables(uri, a_table[0], pkeyName, tableGroup)
                if new_layer is not False:
                    self.handleValueRelations(new_layer, ref_native_col_num, ref_foreign_col_num, selected_layer)

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
