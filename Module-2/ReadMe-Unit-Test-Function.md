Running unit tests is a well known best practice in traditional development.
In a serverless/cloud environment the test cycle is equally important!

Some tests can use mocked services. Mocked services provide a representation that can stand in for the real service. Generally, mocked services are much faster to create, configure, and tear down after testing is done.

For these unit tests, we will show you how to use the Pytest framework with 'moto', an AWS services mocking library.
<!-- Create the test harness... -->
Test-specific dependencies need to be added. These will be used by the testing framework.

Update tests/requirements.txt so that it includes pytest, moto, pytest-freezegun, and requests:

pytest>=7
moto==3.1.19
pytest-freezegun
requests

<!-- Test Handler -->
Paste the following test runner code into tests/unit/test_handler.py :

##

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
import uuid
import pytest
from moto import mock_dynamodb
from contextlib import contextmanager
from unittest.mock import patch

USERS_MOCK_TABLE_NAME = 'Users'
UUID_MOCK_VALUE_JOHN = 'f8216640-91a2-11eb-8ab9-57aa454facef'
UUID_MOCK_VALUE_JANE = '31a9f940-917b-11eb-9054-67837e2c40b0'
UUID_MOCK_VALUE_NEW_USER = 'new-user-guid'


def mock_uuid():
    return UUID_MOCK_VALUE_NEW_USER


@contextmanager
def my_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        put_data_dynamodb()
        yield

def set_up_dynamodb():
    conn = boto3.client(
        'dynamodb'
    )
    conn.create_table(
        TableName=USERS_MOCK_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'userid', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userid', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

def put_data_dynamodb():
    conn = boto3.client(
        'dynamodb'
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JOHN},
            'name': {'S': 'John Doe'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JANE},
            'name': {'S': 'Jane Doe'},
            'timestamp': {'S': '2021-03-30T17:13:06.516Z'}
        }
    )

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_list_of_users():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-all-users.json', 'r') as f:
            apigw_get_all_users_event = json.load(f)
        expected_response = [
            {
                'userid': UUID_MOCK_VALUE_JOHN,
                'name': 'John Doe',
                'timestamp': '2021-03-30T21:57:49.860Z'
            },
            {
                'userid': UUID_MOCK_VALUE_JANE,
                'name': 'Jane Doe',
                'timestamp': '2021-03-30T17:13:06.516Z'
            }
        ]
        ret = users.lambda_handler(apigw_get_all_users_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

def test_get_single_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'userid': UUID_MOCK_VALUE_JOHN,
            'name': 'John Doe',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

def test_get_single_user_wrong_id():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
            apigw_event['pathParameters']['userid'] = '123456789'
            apigw_event['rawPath'] = '/users/123456789'
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}

@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-post-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == UUID_MOCK_VALUE_NEW_USER
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

@pytest.mark.freeze_time('2001-01-01')
def test_add_user_with_id():
    with my_test_environment():
        from src.api import users
        with open('./events/event-post-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"userid\":\"123456789\"}')
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == '123456789'
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

def test_delete_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-delete-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}
# Add your unit testing code here

##

<!-- Test harness explained... -->
Before running unit tests, you must set up a test environment. 
In the test_handler.py script, the test_environment() method injects a mock DynamoDB into the environment, 
then set_up_dynamodb() creates a mock Users table, and finally put_data_dynamodb() creates the test data.
The tests and test events use universally unique identifiers (UUIDs). The same UUIDs used for the mock data will be used in the tests.

##

def put_data_dynamodb():
    conn = boto3.client(
        'dynamodb'
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JOHN},
            'name': {'S': 'John Doe'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JANE},
            'name': {'S': 'Jane Doe'},
            'timestamp': {'S': '2021-03-30T17:13:06.516Z'}
        }
    )

##

Because the tests use a mock DynamoDB, they are not intended to verify database updates. The goal is to test that responses to specific events are what we expect based on the mock data.

After the testing environment is set up, the harness can run individual test cases.

Each test case has a similar structure:

1.Set up the test environment
2.Load a test event (JSON file)
3.Define the expected response event (JSON)
4.Pass the event to the Lambda handler method
5.Verify the result matches the expected response

Additionally, a test may have a @patch decorator which temporarily replaces some environment data while the test runs. For example, setting an environmental variable for USERS_TABLE, or instructing AWS X-Ray to log errors rather than fail in case the context is missing.
<!-- Example test - list all users -->
Here is a typical test which demonstrates the structure to verify the list all users API endpoint:
##

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_list_of_users():
    with test_environment():
        from src.api import users
        with open('./events/event-get-all-users.json', 'r') as f:
            apigw_get_all_users_event = json.load(f)
        expected_response = [
            {
                'userid': UUID_MOCK_VALUE_JOHN,
                'name': 'John Doe',
                'timestamp': '2021-03-30T21:57:49.860Z'
            },
            {
                'userid': UUID_MOCK_VALUE_JANE,
                'name': 'Jane Doe',
                'timestamp': '2021-03-30T17:13:06.516Z'
            }
        ]
        ret = users.lambda_handler(apigw_get_all_users_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

##

Note how the userids are the same UUIDs used to create the data in the test setup.

<!-- Example test - get a single user -->
The next test, test_get_single_user(), uses the same structure, but a different event payload:
##

    def test_get_single_user():
    with test_environment():
        from src.api import users
        with open('./events/event-get-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'userid': UUID_MOCK_VALUE_JOHN,
            'name': 'John Doe',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

##

<!-- Example test - request an non-existent user -->
How about testing what happens when a request comes in for a user that does not exist in the database?

The API is designed to return a status code 200 and an empty value. The same event data for retrieving one specific user can be re-used, but this test will override the userid value with the request path parameters and raw path value:
##
    def test_get_single_user_wrong_id():
        with test_environment():
            from src.api import users
            with open('./events/event-get-user-by-id.json', 'r') as f:
                apigw_event = json.load(f)
                apigw_event['pathParameters']['userid'] = '123456789'
                apigw_event['rawPath'] = '/users/123456789'
            ret = users.lambda_handler(apigw_event, '')
            assert ret['statusCode'] == 200
            assert json.loads(ret['body']) == {}
##
Note: You may choose to implement different business logic. For example, your API could return 404 Not Found HTTP code instead for unknown users.

<!-- Example test - create a user -->
So far, the tests have verified that the API works for reading data. The next test checks if Users can be created and updated.

The test loads event data from a JSON file, runs the Lambda handler, and verifies the response userid and timestamps match mock values, and that the returned user name matches the event data:
##

@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_user():
    with test_environment():
        from src.api import users
        with open('./events/event-post-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == UUID_MOCK_VALUE_NEW_USER
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

##
Did you notice the use of two decorators: @patch and @pytest.mark.freeze_time?

The Lambda function will generate and assign a new UUID if one is not present in the event data. The @patch decorator replaces the standard random uuid generator function (uuid.uuid1) with the mock_uuid() defined in test_handler.py.

The mock_uuid() function simply returns a constant UUID_MOCK_VALUE_NEW_USER, which is compared in the later assertion.

Similarly, when the Lambda function sets the timestamp, it will use whatever happens to be the current date and time. That would be difficult to verify, so the test *freezes time at a fixed point with the @pytest.mark.freeze_time decorator, and uses that same timestamp when checking the data in the returned event.

<!-- Example test - update a user -->
When a user identifier is in the payload, the Lambda function is expected to use it to update existing data. When this happens, the last update timestamp should be set to the current date and time. The method test_add_user_with_id will verify this scenario by modifying event data so that a user ID is specified in the event payload.

The results will be verified to check that the same user ID in the update is in the response, in this case the userid is "123456789":

##
@pytest.mark.freeze_time('2001-01-01')
def test_add_user_with_id():
    with test_environment():
        from src.api import users
        with open('./events/event-post-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"userid\":\"123456789\"}')
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == '123456789'
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

##

<!-- Example test - delete a user -->
The last test case verifies user deletion. Same pattern : load event (JSON file), run Lambda handler, verify expected response status and data:

##

def test_delete_user():
    with test_environment():
        from src.api import users
        with open('./events/event-delete-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}

##

<!-- Why do you need test events? -->
We've already talked about using test events, but what are they and why are they needed?

Serverless is event driven, so actions require an input event. Events are represented in JSON.

Take a look at the four (4) test event files in the events/ folder:

event-get-all-users.json
event-get-user-by-id
event-put-user.json
event-post-user.json
event-delete-user-by-id.json
All of these test events are chunks of JSON in the same structure, or shape, that API Gateway would deliver to the Lambda function. The events contain properties related to the request, such as resource, path, httpMethod, headers, query & path parameters, body, and more.

<!-- How to create test events -->
Test events are JSON data files that simulate the data that a service would send or receive. But, how do you create these events?

One option, use the SAM CLI to generate events for commonly used services, like API Gateway, S3, SNS, SQS, Cognito.

For example:

##

Admin:~/environment/serverless-workshop/users $ sam local generate-event apigateway aws-proxy
{
  "body": "eyJ0ZXN0IjoiYm9keSJ9",
  "resource": "/{proxy+}",
  "path": "/path/to/resource",
  "httpMethod": "POST",
  "isBase64Encoded": true,
  "queryStringParameters": {
    "foo": "bar"
  },
  "multiValueQueryStringParameters": {
    "foo": [
      "bar"
    ]
  },
  "pathParameters": {
    "proxy": "/path/to/resource"
  },
  "stageVariables": {
    "baz": "qux"
  },
  "headers": {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",

   // ... more JSON, omitted for brevity ... 

##

A second option, find examples of events for all services in the documentation. See the Lambda Guide - Working with other services(click on each service in the table: https://docs.aws.amazon.com/lambda/latest/dg/lambda-services.html to see sample service event sent to lambda)  where each service listing provides example JSON events.

<!-- Run the tests... -->
Before you run the tests, make sure you are in the application directory in the terminal and in the virtual environment, then run pip to install all dependencies. You only need to do this once. :
    pip install -r requirements.txt
    pip install -r ./tests/requirements.txt

Run the unit tests with one of the following command depending on your machine:

    python3 -m pytest tests/unit -v OR python -m pytest tests/unit -v 

<!-- Error returned by API Gateway? -->
First, make sure you have added the necessary dependencies to the requirements.txt file for Python.

Next, look for details of the error in the Lambda function logs in CloudWatch Logs.

