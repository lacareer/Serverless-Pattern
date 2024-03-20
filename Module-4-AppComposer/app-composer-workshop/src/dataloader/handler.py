import json
import boto3
import os
import csv
import codecs

# Create clients to connect to the services
s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')

# Get resource names from the environment for flexibility
bucketName = os.environ['IMPORTBUCKET_BUCKET_NAME']
tableName = os.environ['EMPLOYEES_TABLE_NAME']
csvFileName = 'employees.csv'

def handler(event, context):
   # Open the CSV data file in S3
   try:
       obj = s3.Object(bucketName, csvFileName).get()['Body']
   except Exception as error:
       print(error)
       print('S3 Object could not be opened. Check environment variable. ')

   # Connect to the table in DynamoDB
   try:
       table = dynamodb.Table(tableName)
   except Exception as error:
       print(error)
       print('Error loading DynamoDB table. Check if table was created correctly and environment variable.')

   # Read rows from CSV and insert in batches into the table. 
   # Tip: DictReader is a generator, so the entire data file is not stored in memory
   batch_size = 100
   batch = []

   for row in csv.DictReader(codecs.getreader('utf-8-sig')(obj)):
        if len(batch) >= batch_size:
            write_to_dynamo(batch)
            batch.clear()
        batch.append(row)
   if batch:
      write_to_dynamo(batch)
   return "{'statusCode': 200, 'body': 'Uploaded to DynamoDB Table'}"


# Tip: Extract helper methods to keep the handler() method small.
def write_to_dynamo(rows):
   try:
      table = dynamodb.Table(tableName)
   except Exception as error:
        print(error)
        print('Error loading DynamoDB table. Check if table was created correctly and environment variable.')
        exit()
   try:
      with table.batch_writer() as batch_writer:
         for i in range(len(rows)):
            batch_writer.put_item(
               Item=rows[i]
            )
   except Exception as error: 
        print(error)
        print('Error executing batch_writer')
        exit()
