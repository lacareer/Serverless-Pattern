Although testing in isolation with Unit Tests is quick and effective for small parts of your application, you should also build integration tests. In integration testing, you send requests to API endpoints in the cloud development environment and compare responses with expected results.

We will explain six scenarios to show you how to create integration tests. For production projects, you should create as many detailed integration tests as necessary to exercise your entire API.

<!-- Set up the integration test harness... -->
Prior to running the tests, you need to create a regular and administrative account, and clear previous test data from the data store tables.

Paste the following test environment configuration code into tests/integration/conftest.py :

##

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest
import time

APPLICATION_STACK_NAME = os.getenv('ENV_STACK_NAME', None)
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
    # create regular user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["regularUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}]
    )
    result["regularUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],
                                     Username=result["regularUserName"])
    # get new user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["regularUserName"],
            'PASSWORD': result["regularUserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["regularUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["regularUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    # create administrative user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["adminUserName"] = "adminUser@example.com"
    result["adminUserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["adminUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["adminUserName"],
        Password=result["adminUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["adminUserName"]}]
    )
    result["adminUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],
                                     Username=result["adminUserName"])
    # add administrative user to the admins group
    idp_client.admin_add_user_to_group(UserPoolId=globalConfig["UserPool"],
                                       Username=result["adminUserName"],
                                       GroupName=globalConfig["UserPoolAdminGroupName"])
    # get new admin user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["adminUserName"],
            'PASSWORD': result["adminUserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["adminUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["adminUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["adminUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    return result

def clear_dynamo_tables():
    # clear all data from the tables that will be used for testing
    dbd_client = boto3.client('dynamodb')
    db_response = dbd_client.scan(
        TableName=globalConfig['UsersTable'],
        AttributesToGet=['userid']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['UsersTable'],
            Key={'userid': {'S': item['userid']["S"]}}
        )
    return

@pytest.fixture(scope='session')
def global_config(request):
    global globalConfig
    # load outputs of the stacks to test
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(create_cognito_accounts())
    clear_dynamo_tables()
    return globalConfig


##


Line        number	Description

13-20	    Get stack outputs with information about resources used by the tests

22-92	    Delete and create Amazon Cognito accounts for regular and administrative user, to be used in tests with randomly generated passwords. Get their Identity, Access and refresh JWT tokens

94-106	    Delete any existing data in the Amazon DynamoDB tables used by the tests

108-115	    Initialize the testing environment

<!-- Testing environment script explained -->
Similar to the unit tests, the conftest.py script will set up an environment, but this time with real services and mock data.

Since the test environment will be based on the existing stack, the script will collect and use some of the information from the CloudFormation stack outputs. The get_stack_outputs() method connects to CloudFormation and copies the outputs into a global configuration object for the test cases to use:
##

    APPLICATION_STACK_NAME = os.getenv('ENV_STACK_NAME', None)
    globalConfig = {}

    def get_stack_outputs(stack_name):
        result = {}
        cf_client = boto3.client('cloudformation')
        cf_response = cf_client.describe_stacks(StackName=stack_name)
        outputs = cf_response["Stacks"][0]["Outputs"]
        for output in outputs:
            result[output["OutputKey"]] = output["OutputValue"]
        return result

##

The script next creates mock users in the Amazon Cognito User Pool and mock records in an Amazon DynamoDB database table.

Here are some highlights from create_cognito_accounts() and clear_dynamo_tables() methods:

To test API access by users in each group, the tests require a user account in each group.

<!-- Creation of users requires passwords. The script uses AWS Secrets Manager to generate random passwords:: -->

##

    sm_client = boto3.client('secretsmanager')

    ... non-essential code ...

    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]

##

<!-- An account could be left-over from a failed test cycle, so the script attempts to delete first to ensure a fresh start: -->

##
    idp_client = boto3.client('cognito-idp')
    ...
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["regularUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
##

<!-- The following creates a user in Cognito and confirms signup in code instead of sending a confirmation message: -->

##

    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}]
    )
    result["regularUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],

                                     Username=result["regularUserName"])
##

<!-- Lastly, the script authenticates the user to get the tokens (JWT) for the user: -->

##
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["regularUserName"],
            'PASSWORD': result["regularUserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["regularUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["regularUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
##

<!-- All of these steps are repeated to create an administrative user, who is then added to the administrative user group: -->

##
    idp_client.admin_add_user_to_group(UserPoolId=globalConfig["UserPool"],
                                       Username=result["adminUserName"],
                                       GroupName=globalConfig["UserPoolAdminGroupName"])
##

<!-- Write integration test cases... -->
Paste the following integration testing code into tests/integration/test_api.py:

##

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import requests

new_user_id = ""
new_user = {"name": "John Doe"}

def test_access_to_the_users_without_authentication(global_config):
    response = requests.get(global_config["APIEndpoint"] + '/users')
    assert response.status_code == 401

def test_get_list_of_users_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + '/users',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403

def test_deny_post_user_by_regular_user(global_config):
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=json.dumps(new_user),
        headers={'Authorization': global_config["regularUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403

def test_allow_post_user_by_administrative_user(global_config):
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=json.dumps(new_user),
        headers={'Authorization': global_config["adminUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['name'] == new_user['name']
    global new_user_id
    new_user_id = data['userid']

def test_deny_post_invalid_user(global_config):
    new_invalid_user = {"Name": "John Doe"}
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=new_invalid_user,
        headers={'Authorization': global_config["adminUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 400

def test_get_user_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'/users/{new_user_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403

##

<!-- Line by line explanation of code... -->
Line    number	Description
10-12	Test that unauthenticated user has access to the list of users, expecting HTTP 401 status code as a response
14-19	Test that authenticated non-administrative user has access to the list of users, expecting HTTP 403 status code as a response
21-28	Test that authenticated non-administrative user can create a new user, expecting HTTP 403 status code as a response
30-41	Test that authenticated administrative user can create a new user, expecting response with newly created user data
43-51	Test that authenticated administrative user can create a new user using invalid request payload (wrong field name case), expecting HTTP 400 status code as a response

<!-- Test cases explained -->
Now that the testing environment is ready, you can write test cases. We provide you with a few scenarios to show an approach to integration testing. In production projects, we advise that you cover more aspects of your system with your integration tests.

Start by verifying that access is denied without authentication:

##
def test_access_to_the_users_without_authentication(global_config):
    response = requests.get(global_config["APIEndpoint"] + '/users')
    assert response.status_code == 401
##

<!-- Next, verify that a valid authenticated 'regular' user can NOT access the list of other users. Regular users should not be able to view others users data. -->
##
def test_get_list_of_users_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + '/users',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403
##

<!-- check regular user  -->
Also, check if regular user can create a user account. Note that this isn't a use case for user self-registering for the service. In a case a user creates an account for themselves, a path should include user ID that matches Cognito principal ID in the JWT token used for authorization:
##
def test_deny_post_user_by_regular_user(global_config):
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=json.dumps(new_user),
        headers={'Authorization': global_config["regularUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403
##

<!-- Verify that an administrative user can create an account, and the data returned matches the data submitted in the request: -->

##
def test_allow_post_user_by_administrative_user(global_config):
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=json.dumps(new_user),
        headers={'Authorization': global_config["adminUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['name'] == new_user['name']
    global new_user_id
    new_user_id = data['userid']
##

<!-- Test when data submitted does not match the format the backend expects. Note the uppercase N in the field "name": -->

##
def test_deny_post_invalid_user(global_config):
    new_invalid_user = {"Name": "John Doe"}
    response = requests.post(
        global_config["APIEndpoint"] + '/users',
        data=new_invalid_user,
        headers={'Authorization': global_config["adminUserIdToken"],
                 'Content-Type': 'application/json'}
    )
    assert response.status_code == 400

##

<!-- Verify that regular users can NOT access another users newly created data. Regular users do not need to know who else is using the service: -->
##
def test_get_user_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'/users/{new_user_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403
##

<!-- Run the tests... -->
Run the integration tests with the following commands and make sure to be the project directory and in your virtual environment:

    export ENV_STACK_NAME=ws-serverless-patterns-users
    python -m pytest tests/integration -v

<!-- EXTRA CREDIT -->
Add integration tests to cover the following scenarios:

Verify that regular users have access to their own data
Verify that regular users can change their own data
Verify that regular users can delete their own data
Verify that an administrative user can list all users
Verify that an administrative user can delete an existing user