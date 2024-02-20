# https://catalog.workshops.aws/serverless-patterns/en-US/module3/sam-python

You will use Serverless Application Model (SAM) templates with Python to build a synchronous and idempotent microservice for Orders.

<!-- Tasks to accomplish: -->

1. Create an API Gateway and DynamoDB for Orders
2. Create Lambda functions for adding, retrieving, listing, editing and canceling orders
3. Create a Lambda layer to share common code
4. Enforce idempotency for the functions
5. Add observability to the functions

<!-- Module setup -->

  Go to Readme-Setup.md

<!-- NOTE -->
Before you can explore idempotency to reliably send orders to restaurants, you need an Orders microservice, with the following components:

- Orders database table
- Function(s) to create, read, update, and delete Orders
- API to connect requests to your Orders function(s)

This trio of resources may sound familiar from the Users module. To get started faster, we've provided database, API, and function resources for the SAM template.

<!-- Add the resources to template.yaml -->
In Cloud9, go to the ws-serverless-patterns/orders directory and open template.yaml. Paste the following template into template.yaml to set up the Orders table, API gateway and AddOrder function:

File: ~/path_to_project/ws-serverless-patterns/orders/template.yaml

##
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for orders

Globals:
  Api:
    TracingEnabled: true  # Enables AWS X-Ray tracing for the API Gateway.

Parameters:
  UserPool:
    Type: String
    Description: User Pool ID produced by the Users module
    #default: "ca-central-1_wOPEnHdap"
   
Resources: 
  OrdersTable:  # Creates the DynamoDB table with userId and orderId as the keys
    Type: AWS::DynamoDB::Table
    Properties:
      AttributeDefinitions:
        - AttributeName: "userId"
          AttributeType: "S"
        - AttributeName: "orderId"
          AttributeType: "S"
      KeySchema:  # Specifies the primary key. For Orders, the key is a composite of "userId" and "orderId".
        - AttributeName: "userId"
          KeyType: "HASH"
        - AttributeName: "orderId"
          KeyType: "RANGE"
      BillingMode: PAY_PER_REQUEST  # user pay-per-request billing

  WorkshopApiGateway:  # Defines the API Gateway
    Type: AWS::Serverless::Api 
    Properties:
      StageName: Prod
      Auth:
        DefaultAuthorizer: Module3CognitoAuthorizer
        Authorizers:
          Module3CognitoAuthorizer:  # Sets Cognito user pool as default authorizer for API requests
            UserPoolArn: !Sub "arn:aws:cognito-idp:${AWS::Region}:${AWS::AccountId}:userpool/${UserPool}"
  AddOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/create_order.lambda_handler
      Runtime: python3.9
      Tracing: Active
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /orders
            Method: post
            RestApiId: !Ref WorkshopApiGateway
Outputs:
  Module3ApiEndpoint:  # Returns the API URL
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${WorkshopApiGateway}.execute-api.${AWS::Region}.amazonaws.com/Prod"
  OrdersTable:
    Description: "DynamoDb Orders Table"
    Value: !Ref OrdersTable

##

<!-- Create a function to add Orders  -->
Create a new file called ws-serverless-patterns/orders/src/api/create_order.py and insert the following code:

##
import os
import boto3
from decimal import Decimal
import json
import uuid
from datetime import datetime

# Globals
orders_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def add_order(event, context):
    detail = json.loads(event['body'])
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
    detail['orderId'] = orderId
    detail['status'] = 'PLACED'
    return detail

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

##

<!-- Deploy the Orders microservice -->
Your microservice is not complete, but this is still a good time to deploy so you will be ready to set up your test harness.

Build and deploy the SAM template. You will need (or modify the UserPool parameter in template and set the default to the USER_POOL_ID from the console) to get the Cognito UserPoolID value from the Users module. Your API Gateway needs that to authenticate requests.
# Authorizer
This module does not use a custom Lambda authorizer, so you can focus on learning how to add idempotence to your service.

<!-- To get the User Pool ID -->
Open the CloudFormation console

Find the stack named: ws-serverless-patterns-users

Note: If you deployed resources in the setup step, your stack name will have a suffix, similar to: ws-serverless-patterns-users-1KV5ZQTUAGJUJ

Select the outputs tab

Copy the value for UserPool -- for example: us-east-2_123456789.

<!-- To build with SAM -->
1. In the IDE terminal tab, navigate to the project directory:

  cd ~/path_to_project/ws-serverless-patterns/orders

2. Build and deploy the current project:

  sam build && sam deploy --guided --stack-name ws-serverless-patterns-orders

Providing the following responses to the prompts:

1.For UserPool: paste the value copied from the preceding steps.
2.Deploy this changeset: enter Y for Yes.
3.Press Enter to accept the default values for all other variables.

During the first deployment, you use the --guided option with a preset stack-name. 
This mode prompts you for the required parameters, provides default options, and saves your selections to a configuration file. 
SAM CLI retrieves the parameters from that configuration file on subsequent, non-guided deploys, to speed up the deploy process.

<!-- Congratulations! -->
You've got the beginning of an Orders microservice! In the next few steps, you'll add tests and full functionality before making it idempotent...

<!-- 1.1 - Set up tests -->
Before we go too far, let’s set up integration tests to ensure the API behaves according to the specification.

For integration tests, you send requests to API endpoints in the development environment cloud and compare responses with expected results.

We will provide you with basic integration tests, so you can minimally validate the API. For production projects, you should create as many detailed integration tests as necessary to exercise your entire API.

<!-- Add testing dependencies -->
Open file tests/requirements.txt and copy the following dependencies into it.
  pytest
  boto3
  requests

In the IDE terminal tab, run the following commands to install the libraries and verify pytest works:

  pip install -r tests/requirements.txt
  pytest --version

<!-- Set up test harness -->
To run your tests against the API, you’ll need a test user and to ensure the environment is clean before starting the test suite. The testing tool you will be using is called Pytest which can share ‘fixtures’ across multiple tests  to reduce the complexity of your tests.

The Python test script harness creates a Pytest fixture in `global_config()`` which sets up the test environment. The test environment is based on your existing stack, so the script first connects to CloudFormation to get stack outputs used by the test cases.

To ensure the identity store is ready, the code deletes any existing users. Then, it creates a test user with random credentials generated by Secrets Manager. After creating that test user, the code calls admin_confirm_sign_up() to automatically confirm the user. Then, it calls initiate_auth() to request an access token that is stored in the result dictionary.

Lastly, the code deletes any pre-existing items in the Orders database table.

Replace the contents of the file named tests/integration/conftest.py with the following code.

##
import boto3
import os
import pytest
import uuid
import json
from datetime import datetime
from decimal import Decimal

APPLICATION_STACK_NAME = os.getenv('USERS_STACK_NAME', None)
MODULE3_STACK_NAME = os.getenv('ORDERS_STACK_NAME', None)
globalConfig = {}

def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        result[output["OutputKey"]] = output["OutputValue"]
    return result

def create_cognito_accounts():
    result = {}
    sm_client = boto3.client('secretsmanager')
    idp_client = boto3.client('cognito-idp')
    
    # Get a random password from Secrets Manager
    secrets_manager_response = sm_client.get_random_password(
        ExcludeCharacters='"''`[]{}():;,$/\\<>|=&', RequireEachIncludedType=True)
    result["user1UserName"] = "user1User@example.com"
    result["user1UserPassword"] = secrets_manager_response["RandomPassword"]

    # Delete any existing users before creating new
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["user1UserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('User1 not found; no deletion necessary. Continuing...')

    # Create a new user
    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["user1UserName"],
        Password=result["user1UserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["user1UserName"]}]
    )
    result["user1UserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],
                                     Username=result["user1UserName"])

    # Get new user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["user1UserName"],
            'PASSWORD': result["user1UserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["user1UserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["user1UserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["user1UserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]

    return result

def clear_dynamo_tables():
    """
    Clear all pre-existing data from the tables prior to testing.
    """
    dbd_client = boto3.client('dynamodb')
    db_response = dbd_client.scan(
        TableName=globalConfig['OrdersTable'],
        AttributesToGet=['userId', 'orderId']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['OrdersTable'],
            Key={'userId': {'S': item['userId']["S"]},
                 'orderId': {'S': item['orderId']["S"]}}
        )

@pytest.fixture(scope='session')
def global_config(request):
    """
    Load stack outputs, create user accounts, and clear database tables.
    """
    global globalConfig
    # load outputs of the stacks to test
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(get_stack_outputs(MODULE3_STACK_NAME))
    globalConfig.update(create_cognito_accounts())
    clear_dynamo_tables()
    return globalConfig

##

<!-- Write your first integration tests -->
The following Python test code verifies that orders can be placed for a restaurant.

test_access_orders_without_authentication() - verifies that non-authenticated access attempts are rejected
test_add_new_order() - verifies that a user can successfully place an order

The new order test sends a POST request to the orders endpoint with JSON representing a mock order. That order has an ID generated with the uuid library that will be guaranteed to be unique. The test sets the authorization header to the user1UserIdToken obtained previously and verifies the response status is 200 (OK) and response body contains the expected order information. Finally, it stores the orderId in a global dictionary for subsequent tests.

Paste the following integration test code into tests/integration/test_api.py:

##
import json
import requests
import logging
import time
import uuid
import pytest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

order_1 = {
    "restaurantId": 1,
    "orderId": str(uuid.uuid4()),
    "orderItems": [
        {
            "id": 1,
            "name": "Spaghetti",
            "price": 9.99,
            "quantity": 1
        },
        {
            "id": 2,
            "name": "Pizza - SMALL",
            "price": 4.99,
            "quantity": 2
        },
    ],
    "totalAmount": 19.97
}

@pytest.fixture
def orders_endpoint(global_config):
  '''Returns the endpoint for the Orders service'''
  orders_endpoint = global_config["Module3ApiEndpoint"] + '/orders'
  logger.debug("Orders Endpoint = " + orders_endpoint)
  return orders_endpoint

@pytest.fixture
def user_token(global_config):
  '''Returns the user_token for authentication to the Orders service'''
  user_token = global_config["user1UserIdToken"]
  logger.debug("     User Token = " + user_token)
  return user_token


def test_access_orders_without_authentication(orders_endpoint):
  response = requests.post(orders_endpoint)
  assert response.status_code == 401


def test_add_new_order(global_config, orders_endpoint, user_token):
  response = requests.post(orders_endpoint, data=json.dumps(order_1),
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )
  logger.debug("Add new order response: %s", response.text)
  assert response.status_code == 200
  orderInfo = response.json()
  orderId = orderInfo['orderId']
  logger.debug("New orderId: %s", orderId)
  global_config['orderId'] = orderId
  assert orderInfo['status'] == "PLACED"

##

<!-- Prepare the test environment -->
The test harness requires two environment variables to retrieve resource outputs from CloudFormation.

In your terminal run the following commands:

  export USERS_STACK_NAME=ws-serverless-patterns-users
  export ORDERS_STACK_NAME=ws-serverless-patterns-orders

<!-- View stack outputs for Users module -->
Run the following commands, and make sure you get output containing OutputKey’s and OutputValues.

  cd ~/environment/ws-serverless-patterns/orders
  aws cloudformation describe-stacks --stack-name $USERS_STACK_NAME --query "Stacks[0].Outputs"

<!-- Run the tests -->
In the IDE terminal tab, run the following commands:

  cd ~/environment/ws-serverless-patterns/orders
  pytest tests/integration -v

<!-- Congratulations! -->
You’ve deployed the Orders service API with working integration tests!

Note: If your tests do not pass, put on your debugging hat and ask for help to get your tests running before moving forward.

<!-- 1.2 - Create a layer -->
You may have noticed repeated code in your functions. You also might be wondering how to use shared code from other teams.

One way to reuse code or third party libraries is with Lambda Layers .

In fact, Powertools for AWS Lambda , a shared code library, simplifies implementing idempotence and is deployed in a layer. So, let's take a few minutes to learn how to setup and use layers!

# From the Lambda Developer Guide:

Lambda layers provide a convenient way to package libraries and other dependencies that you can use with your Lambda functions. Layers promote code sharing and separation of responsibilities so that you can iterate faster on writing business logic.

You can create and use a Lambda layer in three steps:

1.Identify and extract the shared code
2.Define a layer in the SAM template
3.Add the layer to your Lambda function configuration

<!-- Identify and extract shared code... -->
All of the following features need to retrieve an order from the database: When you want to reuse shared code, you will add the layer when you configure those operations.

Get Order
Edit Order
Cancel Order
Create a file named src/layers/utils.py and add the following code.

##
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
##

The shared layer code imports the Key class and boto3 module to connect and query the database table. The get_order function uses the two parameters: userId and orderId to create a KeyConditionExpression for finding the order in the database. Although that should find a singular result, the code loops through all returned Items in the database response and returns the first item.

This code is needed in several of the single-purpose API functions, so the next step is to build a layer that contains it instead of duplicating it.

<!-- Create a Lambda Layer -->
The Lambda layer will contain the code you previously defined and will be available to other Lambda functions.

Add the following YAML at the bottom of the Resources section of your template.yaml file.

##
  PyUtils:
    Type: AWS::Serverless::LayerVersion
    Properties:
        LayerName: pyutils
        Description: Shared utilities for Orders service 
        ContentUri: src/layers/
        CompatibleRuntimes:
          - python3.10
        RetentionPolicy: Delete
    Metadata:
      BuildMethod: python3.10
##

As you can probably guess, the template type AWS::Serverless::LayerVersion provides the shared layer of functionality.

LayerName: A name for the layer version.
ContentUri: path to the folder containing the dependencies that will be packaged as a layer.
CompatibleRuntimes: runtime environments that can use this particular layer
RetentionPolicy: "Delete" in this case means that when you delete the stack, the layer will also be deleted.
Metadata: The BuildMethod metadata indicates which version of Python was used to build the layer.

# Tip
When you run your build, take note of the log output. It should say, "requirements.txt file not found" and continue the build without dependencies. This is a good reminder that if your layer has dependencies, you can add them by creating a requirements.txt file in the layer directory.

<!-- Build, deploy, and run tests -->
To verify that creating the layer works, run the build, deploy, then re-run your integration tests.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

# Troubleshooting tip
If you see only error messages when running your tests, make sure the environment variables for the stack names are set.

You aren't using the layer yet, but navigate to the Lambda console to see it. You'll find Layers in the Additional resources on the left navigation bar. From there, you should see pyutils in the list!

<!-- Congratulations! -->
You’ve just created your first Layer! In the steps ahead, you will use open source utilities provided by a layer.

<!-- 1.3 - Get Order with layer -->
In this step, your Lambda function will retrieve an order with the get_order() method from the pyutils Lambda layer you created in the previous step.
The handler calls get_order() from pyutils to retrieve the order details from the DynamoDB table in the TABLE_NAME environment variable. If the query is successful, the function returns as JSON response with the order information and a success status code.

The Lambda handler is a great place to do input retrieval and validation. You keep business logic isolated, testable, and reuseable in the layer.

Create a new file named src/api/get_order.py and paste in the following code.

##
import simplejson as json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
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
##

<!-- Write an integration test -->
The following function verifies that the API retrieves an order based on a specific order ID. It sends a GET request to the specified API endpoint with the order ID and user authentication token in the header. Then, it parses the response JSON and verifies that the response contains expected values for the order ID, order status, total amount, restaurant ID, and the number of order items.

Add the following test to the tests/integration/test_api.py file.
##
def test_get_order(global_config, orders_endpoint, user_token):
  response = requests.get(orders_endpoint + "/" + global_config['orderId'],
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )

  logger.debug(response.text)
  orderInfo = json.loads(response.text)
  assert orderInfo['orderId'] == global_config['orderId']
  assert orderInfo['status'] == "PLACED"
  assert orderInfo['totalAmount'] == 19.97
  assert orderInfo['restaurantId'] == 1
  assert len(orderInfo['orderItems']) == 2

##

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If all goes well, you will see a message stating 3 passed.

<!-- 1.4 - List Orders -->
Our users want to be able to see a list of all orders they have placed. In this step, create a Lambda function which will return all orders for the User based on the user ID value in the request context.

Create a new file named src/api/list_orders.py and paste in the following code.

##
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
##

<!-- Add function and API resources to IaC -->
Much like the previously created GetOrderFunction resource, this Lambda resource identifies the source code location, read permissions for the Orders table, and the environment variable for the Orders table name. The API Gateway event source mapping path is /orders, providing requesters a unique path to request all order data for a user.

Add the following function and API endpoint resources to the Resources section in template.yaml.

##
  ListOrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/list_orders.lambda_handler
      Runtime: python3.10
      Tracing: Active
      Policies:
        DynamoDBReadPolicy:
          TableName: !Ref OrdersTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /orders
            Method: get
            RestApiId: !Ref WorkshopApiGateway
##

<!-- Write an integration test -->
This test case makes a request to the new list_orders() function and verifies that it returns one mock order created in the global_config() fixture.

Add the following code at the bottom of the tests/integration/test_api.py file.

##
def test_list_orders(global_config, orders_endpoint, user_token):
  response = requests.get(orders_endpoint,
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )
  orders = json.loads(response.text)
  assert len(orders['orders']) == 1
  assert orders['orders'][0]['orderId'] == global_config['orderId']
  assert orders['orders'][0]['totalAmount'] == 19.97
  assert orders['orders'][0]['restaurantId'] == 1
  assert len(orders['orders'][0]['orderItems']) == 2  

##

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If the test succeeds, you will see a green message stating 4 passed.

<!-- 1.5 - Edit an Order -->
Customers can modify an Order before the restaurant has set the status to ACKNOWLEDGED.
The code defines two functions lambda_handler and edit_order. The lambda_handler() is the entry point for the AWS Lambda function. It calls edit_order() which creates an updated order to store in the database. The updated order information is returned to the Customer.

Remember the Lambda layer you created to get orders? You will include that layer again to reuse the get_order() function.

Create a new file named src/api/edit_order.py and paste in the following code.
##
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

##

<!-- Add function and API resources to IaC -->
The following template defines a Lambda function named EditOrderFunction. The Path property of ApiEvent specifies the /orders/{orderId} path, when invoked by an HTTP PUT method.

At this point, the settings should be familiar, but take note of the dependency on the PyUtils Lambda Layer which you created previously.

Add the following function and API endpoint resources to the Resources section in template.yaml.

##
  EditOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/edit_order.lambda_handler
      Runtime: python3.10
      Tracing: Active
      Policies:
        DynamoDBCrudPolicy:
          TableName: !Ref OrdersTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
      Layers:
        - !Ref PyUtils
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /orders/{orderId}
            Method: put
            RestApiId: !Ref WorkshopApiGateway
##

<!-- Write an integration test -->
The test_edit_order() function begins by creating a modified order object, simulating what happens when a customer updates their order. Then, it makes a request to the new API Gateway path which executes the new EditOrderFunction. Finally, the API response is compared to the modifiedOrder attributes to ensure the update was successful.

Add the following to the end of the test_api.py file.

##
def test_edit_order(global_config, orders_endpoint, user_token):
  print(f"Modifying order {global_config['orderId']}")

  modifiedOrder = {
    "restaurantId": 1,
    "orderItems": [
        {
            "id": 1,
            "name": "Spaghetti",
            "price": 9.99,
            "quantity": 1
        },
        {
            "id": 2,
            "name": "Pizza - SMALL",
            "price": 4.99,
            "quantity": 1
        },
        {
            "id": 3,
            "name": "Salad - LARGE",
            "price": 9.99,
            "quantity": 1
        },
      ],
      "totalAmount": 25.97
  }

  response = requests.put(
      orders_endpoint + "/" + global_config['orderId'],
      data=json.dumps(modifiedOrder),
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )

  logger.debug(f'Modify order response: {response.text}')
  assert response.status_code == 200
  updatedOrder = response.json()
  assert updatedOrder['totalAmount'] == 25.97
  assert len(updatedOrder['orderItems']) == 3

##

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If everything has gone well, you will see a green message stating 5 passed.

<!-- 1.6 - Cancel an Order -->
The business rules allow a Customer to cancel an Order when it is in the PLACED status and is less than 10 minutes old.

The following Python code defines a Lambda function that cancels an order. It first checks the status and age of the order and raises a custom OrderStatusError exception if the order's status is not PLACED or if the order was placed more than 10 minutes ago.

If the order can be canceled, the function set the order status to CANCELED. The updated order data is returned as the function's output. If an exception is caught, the function returns an error response with the appropriate status code and error message.

Create a new file named src/api/cancel_order.py with the following code.

##
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

##

<!-- Add function and API resources to IaC -->
The following template defines a Lambda function named EditOrderFunction. The Path property of ApiEvent specifies the /orders/{orderId} path, when invoked by an HTTP DELETE method.

At this point, the settings should be familiar, but again take note of the dependency on the PyUtils Lambda Layer which you created previously.

Add the following function and API endpoint resources to the Resources section in template.yaml.

##
  CancelOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/cancel_order.lambda_handler
      Runtime: python3.9
      Tracing: Active
      Policies:
        DynamoDBCrudPolicy:
          TableName: !Ref OrdersTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
      Layers:
        - !Ref PyUtils
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /orders/{orderId}
            Method: delete
            RestApiId: !Ref WorkshopApiGateway

##

<!-- Write an integration test - cancel order -->
Cancel order has two integration tests, and a test hook to transform the data into the required state.

The first test case, test_cancel_order(), verifies that an order in PLACED status and with an order duration of less than 10 minutes is successfully cancelled. It verifies the response code is 200 (success), returned orderId matches the test orderId, and the updated order status is CANCELED.

Add the following to the end of the test_api.py file.

##
def test_cancel_order(global_config, orders_endpoint, user_token):
  print(f"Canceling order {global_config['orderId']}")
  response = requests.delete(
      orders_endpoint + "/" + global_config['orderId'],
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )

  logger.debug(f'Cancel order response: {response.text}')
  assert response.status_code == 200
  orderInfo = json.loads(response.text)
  assert orderInfo['orderId'] == global_config['orderId']
  assert orderInfo['status'] == 'CANCELED'
  
  
def test_cancel_order_in_wrong_status(global_config, orders_endpoint, user_token, acknowledge_order_hook):
  response = requests.delete(orders_endpoint + "/" + global_config['ackOrderId'],
      headers={'Authorization': user_token, 'Content-Type': 'application/json'}
      )
  logger.debug(f'Cancel order response: {response.text}')
  # Verify OrderStatusError exception was raised because status not 'PLACED' as expected.
  assert response.status_code == 400

##

<!-- Write an integration test - status not cancellable -->
The test fixtures up to this point only create orders with PLACED status. The following fixture creates an order in the ACKNOWLEDGED status. The ACKNOWLEDGED status indicates the Order may not be modified or cancelled by the user.

One key component of the test is the yield statement which pauses acknowledge_order_hook() after creating the test order so the test_cancel_order_in_wrong_status() function can attempt to cancel the order. After test_cancel_order_in_wrong_status() completes, the remaining code runs to delete the test event.

Add the following code to the test harness in conftest.py.

##
@pytest.fixture(scope='function')
def acknowledge_order_hook(request):
    """
    Fixture to set up an order to test cancel_order() operation.
     - Before test: Creates an order in the database with "ACKNOWLEDGED" order status
     - After test: Removes previously created order
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(globalConfig['OrdersTable'])

    # Create an order with "ACKNOWLEDGED" status
    order_id = str(uuid.uuid4())
    user_id = globalConfig['user1UserSub']
    order_data = {
        'orderId': order_id,
        'userId': user_id,
        'data': {
            'orderId': order_id,
            'userId': user_id,
            'restaurantId': 2,
            'orderItems': [
                {
                    'name': 'Artichoke Ravioli',
                    'price': 9.99,
                    'id': 1,
                    'quantity': 1
                }
            ],
            'totalAmount': 9.99,
            'status': 'ACKNOWLEDGED',
            'orderTime': datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ'),
        }
    }

    ddb_item = json.loads(json.dumps(order_data), parse_float=Decimal)
    table.put_item(Item=ddb_item)

    globalConfig['ackOrderId'] = order_id

    # Next, the test will run...
    yield

    # After the test runs; delete the item
    key = {
        'userId': user_id,
        'orderId': order_id
    }

    table.delete_item(Key=key)

##

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If everything has gone well, you will see a green message stating 7 passed.

<!-- 2 - Add idempotence -->
Imagine your customer begins to place an order, but their device loses network connection. Their client did not receive a confirmation token. When network access is restored, the client app attempts to place the order again, and receives a success confirmation. The impatient customer, meanwhile, pulled down on their mobile UI to refresh and send the order again...

How many orders were actually placed? One, two, or maybe three? How can you be sure?

With both synchronous and asynchronous APIs, failures happen! Your callers need the ability to retry operations without you worrying about data integrity.

To solve this problem, you will create idempotent operations.

Idempotent operations return the same result when called with the same parameters.

1. A unique identifier for an event
2. Data store to track attempted operations
3. Cache for the results
4. A mechanism to flush operations from the cache, so the data store doesn’t grow indefinitely.

AWS Lambda Powertools for Python (https://docs.powertools.aws.dev/lambda/python/latest/), a suite of utilities for AWS Lambda functions, makes it easy to adopt best practices such as structured logging, custom metrics, tracing, batching, and idempotency .

# Try to submit an order multiple times
Before you fix the problem, write a test and see what happens before idempotency is implemented.

What do you expect will be the result of trying to add the same order three times?

<!-- Write an integration test (try to create duplicate orders) -->
The following code is a unit test for the /orders API endpoint. It sends three POST requests to the API with identical order information to simulate multiple retries. The test expects all returned order IDs should match. It also checks the number of orders returned by a GET request. For that test, it expects two orders - one order that was already in the system, and one new order created by this test.

Add the following code to the end of test_api.py.

##
def test_create_order_idempotency(global_config, orders_endpoint, user_token):

  order_details = {
      "restaurantId": 200,
      "orderId": str(uuid.uuid4()),
      "orderItems": [
          {
              "name": "Pasta Carbonara",
              "price": 14.99,
              "id": 123,
              "quantity": 1
          }
      ],
      "totalAmount": 14.99
  }

  order_data = json.dumps(order_details)
  header_data = {'Authorization': user_token, 'Content-Type': 'application/json'}

  # Attempt to add an order three times!
  # With idempotency, all returned order IDs should match.
  response1 = requests.post(orders_endpoint, data=order_data, headers=header_data)
  response2 = requests.post(orders_endpoint, data=order_data, headers=header_data)
  response3 = requests.post(orders_endpoint, data=order_data, headers=header_data)

  orderId1 = response1.json().get("orderId")
  orderId2 = response2.json().get("orderId")
  orderId3 = response3.json().get("orderId")

  assert orderId1 == orderId2 == orderId3
  assert orderId1 != global_config['orderId']

  # Even though the add_order operation was invoked three times (3x), there should only be two (2) orders:
  #   1. First order created in this test suite by test_add_new_order()
  #   2. Second order created in this idempotence test method
  response = requests.get(orders_endpoint, headers=header_data)
  orders = json.loads(response.text)
  assert len(orders['orders']) == 2

##

<!-- Run the test (expect failure) -->

  pytest tests/integration -v

Thew new test should fail! This is expected.

Why? The reason is that the code tries to add a new Order within an existing order ID. This raises a duplicate key exception. 
That provides data integrity, but an exception is not ideal for a consumer of the API.

<!-- Add idempotence to AddOrder operation -->
Here is what you're going to do:

- Add Lambda Powertools as a layer
- Add an tracking table
- Configure operation to use the table
- Modify the function code

1) Add Lambda Powertools layer in global config
You start by adding the Powertools layer to all of your Lambda functions in the Globals section of your SAM template. You will also add an environment variable that will be available to every Lambda function in the SAM template.

Update the Globals section in the template.yaml file with the following:
##
Globals:
  Api:
    TracingEnabled: true
  Function:
    Environment:
      Variables:
        POWERTOOLS_SERVICE_NAME: orders
    Layers:
      - !Sub arn:aws:lambda:${AWS::Region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:26     

##

2) Add Idempotency table
Let’s improve this experience using the Idempotency  feature in Lambda Powertools.

The first resource you need to add is a database table to track attempted operations. Fortunately, the Powertools documentation  provides a DynamoDB table resource definition you need to add to the Resources section in your SAM template (template.yaml).
##
  IdempotencyTable:
    Type: AWS::DynamoDB::Table
    Properties:
      AttributeDefinitions:
        -   AttributeName: id
            AttributeType: S
      KeySchema:
        -   AttributeName: id
            KeyType: HASH
      TimeToLiveSpecification:
        AttributeName: expiration
        Enabled: true
      BillingMode: PAY_PER_REQUEST

##

3) Update IaC configuration for AddOrderFunction
To access the idempotency table, your Lambda function needs read/write access and the table name. 
Replace your AddOrderFunction resource in the SAM template with the following configuration:

##
  AddOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/create_order.lambda_handler
      Runtime: python3.9
      Tracing: Active
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
        - DynamoDBCrudPolicy:
            TableName: !Ref IdempotencyTable
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
          IDEMPOTENCY_TABLE_NAME: !Ref IdempotencyTable       
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /orders
            Method: post
            RestApiId: !Ref WorkshopApiGateway
##

4) Modify function code to be idempotent
Next, you will make the following changes to create_order.py to make the add order operation idempotent:

Import PowerTools library
Look up the idempotency_table name
Create a DynamoDBPersistenceLayer so the idempotency library can store events and cache results
Decorate the lambda_handler function with @idempotent
With these changes, the add order operation will become idempotent.

How? The @idempotent decorator wraps the lambda_handler function so that invocations first lookup the incoming event in the idempotency_table.

- If the event is not in the table, the decorator invokes the lambda_handler, which in turn calls add_order(). The results are cached and returned. Or...
- If the event has been seen before, the decorator will not invoke the lambda_handler. Instead the decorator will return the previous result from cache, ensuring add_order() will not be called multiple times.

In this example, the entire Lambda handler is treated as a single idempotent operation. If you are only interested in making a specific function idempotent, use the idempotent_function  decorator (see Python PowerTools - idempotency ).

# Note
By default, AWS Lambda Powertools expire idempotency records after one hour (3600 seconds).
Replace the contents of the file src/api/create_order.py with the following. The modified lines are highlighted.

##
import os
import boto3
from decimal import Decimal
import json
import uuid
from datetime import datetime
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.idempotency import (
    IdempotencyConfig, DynamoDBPersistenceLayer, idempotent
)

# Globals
orders_table = os.getenv('TABLE_NAME')
idempotency_table = os.getenv('IDEMPOTENCY_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

persistence_layer = DynamoDBPersistenceLayer(table_name=idempotency_table)

def add_order(event: dict, context: LambdaContext):

    detail = json.loads(event['body'])
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

    detail['orderId'] = orderId
    detail['status'] = 'PLACED'

    return detail


@idempotent(persistence_store=persistence_layer)
def lambda_handler(event, context):
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

##

<!-- Build, deploy, and run tests -->
  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If everything has gone well, you will see a nice green message stating 8 passed.

# Congratulations!
You’ve built your first idempotent API with the @idempotent decorator from the Lambda PowerTools! Now you can be certain of data integrity even when the Customer retries an operation!

<!-- 3 - Add structured logging with PowerTools -->

When you are troubleshooting problems with the orders service, a view of all the data in the order would help.

AWS Lambda PowerTools for Python provides a way to add structured data to your Lambda functions. We'll show you how add data, view the logs, and add detailed structured data too.

# In create_order.py, add the following import for the Powertools Logger.

  from aws_lambda_powertools import Logger

# In the #Globals section, add the following code to create an instance of the Logger:

  logger = Logger()

# Replace detail = json.loads(event['body']) with the following:

    logger.info("Adding a new order")
    detail = json.loads(event['body'])
    logger.info({"operation": "add_order", "order_details": detail})

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

If everything has gone well, you will see a nice green message stating 8 passed.

Explore the logs
Running the integration tests exercises the API and creates a number of log entries. You can view entries in the Console:

<!-- To view log entries in the Console -->

Open the AWS Console to the Lambda Application page .
Select the AddOrderFunction.
Then select the Monitor tab, and then the Logs tab to see recent invocations.
On the first row, choose the LogStream link to open the events in CloudWatch
Select a row with `"message":"Adding a new order"``
You should see a log entry with additional context information, similar to the following:

  {
    "level": "INFO",
    "location": "add_order:28",
    "message": "Adding a new order",
    "timestamp": "2023-09-11 20:44:13,638+0000",
    "service": "orders",
    "xray_trace_id": "1-6439bb1c-76fac8201f182251609e6e90"
  }

This shows you the exact location in your code where this message originated, the service you specified, and other helpful logging information.

Select a row containing "message":{"operation":"add_order"
You should see additional context, similar to the following:

  {
    "level": "INFO",
    "location": "add_order:28",
    "message": {
        "operation": "add_order",
        "order_details": {
            "restaurantId": 1,
            "orderId": "3ce24de9-9e99-40f5-bf5a-34e8eb7648db",
            "orderItems": [
                {
                    "id": 1,
                    "name": "Spaghetti",
                    "price": 9.99,
                    "quantity": 1
                },
                {
                    "id": 2,
                    "name": "Pizza - SMALL",
                    "price": 4.99,
                    "quantity": 2
                }
            ],
            "totalAmount": 19.97
        }
    },
    "timestamp": "2023-09-12 03:28:13,818+0000",
    "service": "orders",
    "xray_trace_id": "1-64ffdacc-654530bc2c48565614713731"
  }

<!-- Add Lambda Context -->
The structural data is a good start for your dev and operations teams to use for troubleshooting.

You can add even more with the Lambda context, which includes Lambda runtime data that can be useful in understanding how our function behaves over time.

To add the context, append @logger.inject_lambda_context to the line before the add_order() function:

  @logger.inject_lambda_context
  def add_order(event: dict, context: LambdaContext):

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

Repeat the steps to find and review logs for the recent invocation.

Here’s a sample entry with additional information highlighted:

{
  "level": "INFO",
  "location": "add_order:28",
  "message": "Adding a new order",
  "timestamp": "2023-09-12 05:26:13,295+0000",
  "service": "orders",
  "cold_start": true,
  "function_name": "ws-patterns-orders-AddOrderFunction-ABCDEF12345",
  "function_memory_size": "128",
  "function_arn": "arn:aws:lambda:us-west-2:123456789012:function:ws-patterns-orders-AddOrderFunction-ABCDEF12345",
  "function_request_id": "f1763161-d13f-4f1e-bba2-b42ab05152b0",
  "xray_trace_id": "1-xxxxxxxxx-004796e533b411a14358b0fd"
}

With a layer and few lines of code, your logs now records the name and ARN for the function, the amount of memory assigned, the request id, cold start status, and an xray trace identifier. This information will help you make informed decisions about application performance and optimization.

<!-- 4 - Add metrics with PowerTools -->

Metrics represent a time-ordered set of data points that are published to CloudWatch. Think of a metric as a variable to monitor. 
The data points represent the values of that variable over time.

You can publish custom metrics to CloudWatch with AWS Lambda Powertools and view statistical graphs of your published metrics with the AWS Management Console.
The Metrics utility in Powertools creates custom metrics asynchronously by logging metrics to standard output following Amazon CloudWatch Embedded Metric Format (EMF - https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html ) .

"The CloudWatch embedded metric format enables you to ingest complex high-cardinality application data in the form of logs and to generate actionable metrics from them. You can embed custom metrics alongside detailed log event data, and CloudWatch automatically extracts the custom metrics so that you can visualize and alarm on them, for real-time incident detection. Additionally, the detailed log events associated with the extracted metrics can be queried using CloudWatch Logs Insights to provide deep insights into the root causes of operational events."

To publish metrics from your application with AWS Lambda Powertools for Python, follow the below steps.

# 1 Add Lambda Powertools metric namespace in global config -->
You need to add another environment variable, POWERTOOLS_METRICS_NAMESPACE, that will be available to every Lambda function in the SAM template.

Update the Globals section in the template.yaml file with the following:

##
Globals:
  Api:
    TracingEnabled: true
  Function:
    Environment:
      Variables:
        POWERTOOLS_SERVICE_NAME: orders
        POWERTOOLS_METRICS_NAMESPACE: ServerlessWorkshop   

##

# 2 Add metric collection to create_order.py
Replace the line from aws_lambda_powertools import Logger with the following:

  from aws_lambda_powertools import Logger, Metrics
  from aws_lambda_powertools.metrics import MetricUnit

In the # Globals section, instantiate the metrics object:

  metrics = Metrics()

Above def add_order() method definition, add the metrics decorator to ensures metrics are flushed on request completion or failure:

  @metrics.log_metrics  # Ensure metrics are flushed after request completion or failure

Prior to the return detail statement in add_order() method add the following lines to collect two metrics:

  logger.info(f"new Order with ID {orderId} saved")
  metrics.add_metric(name="SuccessfulOrder", unit=MetricUnit.Count, value=1)      #SuccessfulOrder
  metrics.add_metric(name="OrderTotal", unit=MetricUnit.Count, value=totalAmount) #OrderTotal

The call to metrics.add_metric() will publish the metrics message to CloudWatch logs in EMF format. These messages will be automatically processed to make the data available for querying with CloudWatch dashboards and CloudWatch log insights.

SuccessfulOrder will be incremented each time an order is placed
OrderTotal will be a daily report on incremental sales totals, without a query to aggregate order data in the database

<!-- Build, deploy, and run tests -->
Run the following commands in your Cloud9 terminal.

  cd ~/path_to_project/ws-serverless-patterns/orders
  sam build && sam deploy
  pytest tests/integration -v

<!-- Explore the logs with metrics -->
To view the embedded metrics, find the log event with message starting with {"_aws":{"Timestamp" as shown below:
# Sample EMF:
{
    "_aws": {
        "Timestamp": 1681763692151,
        "CloudWatchMetrics": [{
            "Namespace": "ServerlessWorkshop",
            "Dimensions": [
                [
                    "service"
                ]
            ],
            "Metrics": [{
                    "Name": "SuccessfulOrder",
                    "Unit": "Count"
                },
                {
                    "Name": "OrderTotal",
                    "Unit": "Count"
                }
            ]
        }]
    },
    "service": "orders",
    "SuccessfulOrder": [
        1
    ],
    "OrderTotal": [
        14.99
    ]
}

Lambda Powertools generated this message and included the custom SuccessfulOrder and OrderTotal metrics, their respective values, and some additional meta data.

Next, we will show you how to view this data on a graph for future integration into a dashboard.

<!-- Generate more metric data -->
Before going further, generate data so that your charts have more data points.

  cd ~/pth_to_project/ws-serverless-patterns/orders
  cmd="pytest tests/integration -v"; for i in $(seq 10); do $cmd; sleep 15; done 

<!-- Explore the metrics dashboard -->
To view metrics that were generated from embedded metric format logs:

Open the CloudWatch console at https://console.aws.amazon.com/cloudwatch/ .
1. In the navigation pane, under Metrics, choose All Metrics.
2. In the Browse tab, within the Custom namespaces section, select ServerlessWorkshop.
3. Select service.
4. To graph a metric, select the check box next to the SuccessfulOrder and OrderTotal metrics.
5. In the time selector above the graph, select Custom, then select 15 minutes.

By default, the metric graph will show the average value for the SuccessfulOrder and OrderTotals metrics. Each order has a count value of one (1), so the average will always be one. Choose the Sum statistic for better insight into the operations.

Update the graph to show the total number of orders completed in a 24 hour period.

Click the Graphed metrics (2) tab to modify the graph.
In the Statistic drop down list, select Sum.
In the Period drop down list, select 5 minutes.

<!-- Congratulations! -->
You've implemented idempotence across several unique functions per operations. And, you've setup structured logs and metrics, all using the Lambda Powertools library as a layer!

Clean up
To delete the many resources created in this module, you could use the Console, but that would take many steps, navigating to several screens, and accepting dozens of confirmations. Instead, you can use the SAM CLI to make cleanup quick and easy!

# STOP!!! Wait! Read me!
If you are continuing with subsequent modules in the workshop, you may want to skip stack deletion.

If you are certain you do not want to continue... you can run the following command to delete the stack:

  cd ~/path/ws-serverless-patterns/orders
  sam delete --stack-name ws-serverless-patterns-orders

The SAM delete command will delete all the resources you deployed in your stack.