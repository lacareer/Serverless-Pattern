import simplejson as json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Globals
ordersTable = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def list_orders(event, context):

    user_id = event['requestContext']['authorizer']['claims']['sub']

    table = dynamodb.Table(ordersTable)
    response = table.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )

    userOrders = [item['data'] for item in response['Items']]

    return userOrders

def lambda_handler(event, context):
    try:
        orders = list_orders(event, context)
        response = {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps({
                "orders": orders
            })
        }
        return response
    except Exception as err:
        raise
