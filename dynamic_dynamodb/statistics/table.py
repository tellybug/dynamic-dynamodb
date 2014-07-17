# -*- coding: utf-8 -*-
""" This module returns stats about the DynamoDB table """
import math
from datetime import datetime, timedelta

from boto.exception import JSONResponseError, BotoServerError
from retrying import retry

from dynamic_dynamodb.aws import dynamodb
from dynamic_dynamodb.log_handler import LOGGER as logger
from dynamic_dynamodb.aws.cloudwatch import (
    CLOUDWATCH_CONNECTION as cloudwatch_connection)


def get_consumed_read_units_percent(table_name, lookback_window_start=15):
    """ Returns the number of consumed read units in percent

    :type table_name: str
    :param table_name: Name of the DynamoDB table
    :type lookback_window_start: int
    :param lookback_window_start: Relative start time for the CloudWatch metric
    :returns: int -- Number of consumed reads
    """
    try:
        metrics = __get_aws_metric(
            table_name, lookback_window_start, 'ConsumedReadCapacityUnits')
    except BotoServerError:
        raise

    if metrics:
        consumed_read_units = int(
            math.ceil(float(metrics[0]['Sum'])/float(lookback_window_start*60)))
    else:
        consumed_read_units = 0

    try:
        consumed_read_units_percent = int(
            math.ceil(
                float(consumed_read_units) /
                float(dynamodb.get_provisioned_table_read_units(table_name)) *
                100))
    except JSONResponseError:
        raise

    logger.info('{0} - Consumed read units: {1:d}%'.format(
        table_name, consumed_read_units_percent))
    return consumed_read_units_percent


def get_throttled_read_event_count(table_name, lookback_window_start=15):
    """ Returns the number of throttled read events during a given time frame

    :type table_name: str
    :param table_name: Name of the DynamoDB table
    :type lookback_window_start: int
    :param lookback_window_start: Relative start time for the CloudWatch metric
    :returns: int -- Number of throttled read events during the time period
    """
    try:
        metrics = __get_aws_metric(
            table_name, lookback_window_start, 'ReadThrottleEvents')
    except BotoServerError:
        raise

    if metrics:
        throttled_read_count = int(metrics[0]['Sum'])
    else:
        throttled_read_count = 0

    logger.info('{0} - Read throttle count: {1:d}'.format(
        table_name, throttled_read_count))
    return throttled_read_count


def get_consumed_write_units_percent(table_name, lookback_window_start=15):
    """ Returns the number of consumed write units in percent

    :type table_name: str
    :param table_name: Name of the DynamoDB table
    :type lookback_window_start: int
    :param lookback_window_start: Relative start time for the CloudWatch metric
    :returns: int -- Number of consumed writes
    """
    try:
        metrics = __get_aws_metric(
            table_name, lookback_window_start, 'ConsumedWriteCapacityUnits')
    except BotoServerError:
        raise

    if metrics:
        consumed_write_units = int(
            math.ceil(float(metrics[0]['Sum'])/float(lookback_window_start*60)))
    else:
        consumed_write_units = 0

    try:
        consumed_write_units_percent = int(
            math.ceil(
                float(consumed_write_units) /
                float(dynamodb.get_provisioned_table_write_units(table_name)) *
                100))
    except JSONResponseError:
        raise

    logger.info('{0} - Consumed write units: {1:d}%'.format(
        table_name, consumed_write_units_percent))
    return consumed_write_units_percent


def get_throttled_write_event_count(table_name, lookback_window_start=15):
    """ Returns the number of throttled write events during a given time frame

    :type table_name: str
    :param table_name: Name of the DynamoDB table
    :type lookback_window_start: int
    :param lookback_window_start: Relative start time for the CloudWatch metric
    :returns: int -- Number of throttled write events during the time period
    """
    try:
        metrics = __get_aws_metric(
            table_name, lookback_window_start, 'WriteThrottleEvents')
    except BotoServerError:
        raise

    if metrics:
        throttled_write_count = int(metrics[0]['Sum'])
    else:
        throttled_write_count = 0

    logger.info('{0} - Write throttle count: {1:d}'.format(
        table_name, throttled_write_count))
    return throttled_write_count


@retry(
    wait='exponential_sleep',
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000,
    stop_max_attempt_number=10)
def __get_aws_metric(table_name, lookback_window_start, metric_name):
    """ Returns a  metric list from the AWS CloudWatch service, may return
    None if no metric exists

    :type table_name: str
    :param table_name: Name of the DynamoDB table
    :type lookback_window_start: int
    :param lookback_window_start: How many minutes to look at
    :type metric_name: str
    :param metric_name: Name of the metric to retrieve from CloudWatch
    :returns: list -- A list of time series data for the given metric, may
    be None if there was no data
    """
    if lookback_window_start < 5:
        lookback_window_start = 5
        logger.warning(
            '{0} - Lookback window cannot be less than 5 minutes. '
            'Setting it to 5 minutes.'.format(table_name))

    try:
        now = datetime.utcnow()
        start_time = now-timedelta(minutes=lookback_window_start)
        end_time = now-timedelta(minutes=lookback_window_start-5)

        return cloudwatch_connection.get_metric_statistics(
            period=300,                 # Always look at 5 minutes windows
            start_time=start_time,
            end_time=end_time,
            metric_name=metric_name,
            namespace='AWS/DynamoDB',
            statistics=['Sum'],
            dimensions={'TableName': table_name},
            unit='Count')
    except BotoServerError as error:
        logger.error(
            'Unknown boto error. Status: "{0}". '
            'Reason: "{1}". Message: {2}'.format(
                error.status,
                error.reason,
                error.message))
        raise
