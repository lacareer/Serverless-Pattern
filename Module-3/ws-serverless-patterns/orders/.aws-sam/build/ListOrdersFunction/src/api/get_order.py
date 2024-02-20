import simplejson as json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
#imported layer (fileName and method in file/code)
from utils import get_order 

# Globals
ordersTable = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    user_id = event['requestContext']['authorizer']['claims']['sub']
    orderId = event['pathParameters']['orderId']

    try:
        orders = get_order(user_id, orderId)
        response = {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(orders)
        }
        return response
    except Exception as err:
        raise
