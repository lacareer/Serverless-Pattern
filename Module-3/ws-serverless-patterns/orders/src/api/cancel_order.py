import simplejson as json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from utils import get_order

# Custom exception
class OrderStatusError(Exception):
    status_code = 400
    
    def __init__(self, message):
        super().__init__(message)

# Globals
ordersTable = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def cancel_order(event, context):
    userId = event['requestContext']['authorizer']['claims']['sub']
    orderId = event['pathParameters']['orderId']

    order = get_order(userId, orderId)
    if order['status'] != 'PLACED':
      error_message = f"Order: {orderId} Status: {order['status']} Error: Order cannot be cancelled. Expected status: 'PLACED'." 
      raise OrderStatusError(error_message)

    orderAge = datetime.utcnow() - datetime.strptime(order['orderTime'], '%Y-%m-%dT%H:%M:%SZ')
    if orderAge.seconds > 600:
      raise OrderStatusError(f"Order {orderId} Created: {str(round(orderAge.seconds/60, 2))} minutes ago. Error: Order cannot be cancelled. Expected < 10 min.")
    
    table = dynamodb.Table(ordersTable)
    response = table.update_item(
      Key={'userId': userId, 'orderId': orderId},
      UpdateExpression="set #d.#s=:s",
      ExpressionAttributeNames={
        '#d': 'data',
        '#s': 'status'
      },
      ExpressionAttributeValues={
        ':s': 'CANCELED'
      },
      ReturnValues="ALL_NEW"
    )

    return response['Attributes']['data']

def lambda_handler(event, context):
    try:
        updated = cancel_order(event, context)
        response = {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(updated)
        }
        return response
    except OrderStatusError as oe:
      return {
        "statusCode": oe.status_code,
        "body": str(oe)
      }
    except Exception as err:
        logger.exception(err)
        raise

