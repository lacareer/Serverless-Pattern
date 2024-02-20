import simplejson as json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
from utils import get_order

# Globals
ordersTable = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def edit_order(event, context):
    userId = event['requestContext']['authorizer']['claims']['sub']
    orderId = event['pathParameters']['orderId']
    newData = json.loads(event['body'], parse_float=Decimal)
    newData['userId'] = userId
    newData['orderId'] = orderId

    order = get_order(userId, orderId)
    if order['status'] != 'PLACED':
      raise Exception(f"Cannot cancel Order {orderId}. Status = {order['status']} - Expected: PLACED")

    newData['status'] = order['status']
    newData['orderTime'] = order['orderTime']
    ddb_item = {
                'orderId': orderId,
                'userId': userId,
                'data': newData
            }
    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    table = dynamodb.Table(ordersTable)
    response = table.put_item(Item=ddb_item)

    return get_order(userId, orderId)


def lambda_handler(event, context):
    try:
        updated = edit_order(event, context)
        response = {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(updated)
        }
        return response
    except Exception as err:
        raise
