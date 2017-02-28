# -*- coding: utf-8 -*-
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    copyright            : (C) 2017 by William Habelt / Sourcepole AG
#    email                : wha@sourcepole.ch


import psycopg2


class RelationRetriever:
    """This class is responsible for retrieving information from the database."""

    def __init__(self, cur=None):
        self.cur = cur
        self.layer = None

    def setLayer(self, layer):
        self.layer = layer

    def retrieveReferencedTables(self, uri):
        """Retrieve a list of layer id's which are referenced in a foreign key by the selected layer."""
        selected_oid = self.retrieveSelectedOid(uri)

        fk_query = "SELECT confrelid FROM pg_constraint WHERE conrelid='%s' AND contype = 'f'" % selected_oid
        self.cur.execute(fk_query)
        referenced_layers = self.cur.fetchall()

        return referenced_layers

    def retrieveSelectedOid(self, uri):
        """Retrieve the oid of the selected layer."""
        oid_query = "SELECT oid FROM pg_class WHERE relname='%s'" % uri.table()
        self.cur.execute(oid_query)
        layer_oid = self.cur.fetchone()

        return layer_oid[0]

    def retrieveForeignCol(self, uri):
        """Retrieve the number of the field which is referenced in the foreign key relation."""
        selected_oid = self.retrieveSelectedOid(uri)
        fkey_query = "SELECT confkey FROM pg_constraint WHERE conrelid = '%s' AND confrelid = %s AND contype = 'f'" % (selected_oid, self.layer)
        self.cur.execute(fkey_query)
        fkey_column = self.cur.fetchall()

        for column in fkey_column:
            ref_foreign_col_num = column[0][0]

        return ref_foreign_col_num

    def retrieveNativeCol(self, uri):
        """Retrieve the number of the field which makes a reference in the foreign key relation."""
        selected_oid = self.retrieveSelectedOid(uri)
        nfield_query = "SELECT conkey FROM pg_constraint WHERE conrelid = '%s' AND confrelid = %s AND contype = 'f'" % (selected_oid, self.layer)
        self.cur.execute(nfield_query)
        nfield_column = self.cur.fetchall()

        for column in nfield_column:
            ref_native_col_num = column[0][0]

        return ref_native_col_num

    def retrieveTablePrimaryKeyName(self):
        """Retrieves the string name of the field that is the primary key of the table."""
        table_pkey = self.retrieveTablePrimaryKey()

        pkey_query_2 = "SELECT attname FROM pg_attribute WHERE attrelid='%s' AND attnum = '%s'" % (self.layer, table_pkey)
        self.cur.execute(pkey_query_2)
        att_names = self.cur.fetchall()

        for att_name in att_names:
            return att_name[0]

    def retrieveTablePrimaryKey(self):
        """Retrieves the field number of the primary key in the table."""
        pkey_query_1 = "SELECT conkey FROM pg_constraint WHERE conrelid = '%s' AND contype = 'p'" % self.layer
        self.cur.execute(pkey_query_1)
        pkey_column = self.cur.fetchall()

        for column in pkey_column:
            return column[0][0]

    def retrieveForeignTables(self):
        """Retrieve the string name of the id of the table."""
        ftable_query = "SELECT relname FROM pg_class WHERE oid='%s'" % self.layer
        self.cur.execute(ftable_query)
        foreign_tables = self.cur.fetchall()

        return foreign_tables
