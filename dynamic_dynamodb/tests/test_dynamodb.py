# -*- coding: utf-8 -*-
""" Test dynamodb utils """
import unittest

from moto import mock_dynamodb2

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.table import Table

from dynamic_dynamodb.aws import dynamodb

class TestDynamodb(unittest.TestCase):

    @mock_dynamodb2
    def setUp(self):
        super(TestDynamodb, self).setUp()

    @mock_dynamodb2
    def test_list_no_tables(self):
        tables = dynamodb.list_tables()
        self.assertEquals([], tables)

    @mock_dynamodb2
    def test_list_many_tables(self):
        for i in range(0,50):
            Table.create('test_%s' % i, schema=[HashKey('key'),])
        tables = dynamodb.list_tables()
        self.assertEquals(50, len(tables))
