import os
import boto3
from decimal import Decimal
import json
import uuid
from datetime import datetime

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from aws_lambda_powertools.utilities.typing import LambdaContext

from aws_lambda_powertools.utilities.idempotency import (
    IdempotencyConfig, DynamoDBPersistenceLayer, idempotent
)

# Globals
logger = Logger()
metrics = Metrics()

orders_table = os.getenv('TABLE_NAME')
idempotency_table = os.getenv('IDEMPOTENCY_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

persistence_layer = DynamoDBPersistenceLayer(table_name=idempotency_table)

@logger.inject_lambda_context
@metrics.log_metrics  # ensures metrics are flushed upon request completion/failure
def add_order(event: dict, context: LambdaContext):
    logger.info("Adding a new order")
    detail = json.loads(event['body'])
    logger.info({"operation": "add_order", "order_details": detail})
    restaurantId = detail['restaurantId']
    totalAmount = detail['totalAmount']
    orderItems = detail['orderItems']
    userId = event['requestContext']['authorizer']['claims']['sub']
    orderTime = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')

    orderId = detail['orderId']

    ddb_item = {
        'orderId': orderId,
        'userId': userId,
        'data': {
            'orderId': orderId,
            'userId': userId,
            'restaurantId': restaurantId,
            'totalAmount': totalAmount,
            'orderItems': orderItems,
            'status': 'PLACED',
            'orderTime': orderTime,
        }
    }
    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    table = dynamodb.Table(orders_table)
    table.put_item(Item=ddb_item)
    
    logger.info(f"new Order with ID {orderId} saved")
    metrics.add_metric(name="SuccessfulOrder", unit=MetricUnit.Count, value=1)      #SuccessfulOrder
    metrics.add_metric(name="OrderTotal", unit=MetricUnit.Count, value=totalAmount) #OrderTotal

    detail['orderId'] = orderId
    detail['status'] = 'PLACED'

    return detail


@idempotent(persistence_store=persistence_layer)
def lambda_handler(event, context):
    """Handles the lambda method invocation"""
    try:
        orderDetail = add_order(event, context)
        response = {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(orderDetail)
        }
        return response
    except Exception as err:
        raise
