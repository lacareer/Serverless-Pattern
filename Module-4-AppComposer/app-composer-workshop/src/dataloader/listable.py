import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
tableName = os.environ['EMPLOYEES_TABLE_NAME']
table = dynamodb.Table(tableName)

def handler(event, context):
  data = table.scan()
  items = json.dumps(data['Items'])
  return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(items),
        "isBase64Encoded": False
    }
