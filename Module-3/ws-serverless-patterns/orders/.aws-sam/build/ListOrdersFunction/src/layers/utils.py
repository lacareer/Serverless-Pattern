from boto3.dynamodb.conditions import Key
import boto3
import os

ordersTable = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def get_order(userId, orderId):
    table = dynamodb.Table(ordersTable)
    response = table.query(
        KeyConditionExpression=(Key('userId').eq(userId) & Key('orderId').eq(orderId))
    )
    
    userOrders = []
    for item in response['Items']:
      userOrders.append(item['data'])
      
    return userOrders[0]
