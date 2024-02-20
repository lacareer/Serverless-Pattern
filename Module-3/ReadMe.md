All resources were created using the AWS console

# Workshop link: https://catalog.workshops.aws/serverless-patterns/en-US

# Note that in commands 'python' could mean 'python3' dependng on your machine - windows or linux
# In this workshop my Ubuntu WSL require using 'python3' 
<!-- Module Setup -->
Setting up resources for a new application can take a lot of time. Introductory tutorials typically show you how to configure resources in the web-based console. The web-based console is easy, but it will slow you down and lead to mistakes.

For production projects, you may need dozens or even hundreds of resources. You will need to provision infrastructure for many developers and environments, such as dev, stage, prod.

In this module, you will use scalable Infrastructure as Code (IaC) techniques to define, deploy, and test service resources and code.

We'll show you how to use AWS Serverless Application Model (SAM)  and the SAM CLI to quickly build and deploy your application.

<!-- Create a project with SAM -->
We have provided a 'cookiecutter' file to create the initial project structure. SAM will ask for some info and then create the structure.

In the Cloud9 terminal, navigate to the ~/environment directory or to you projet directory in VS Code.

Run sam init and accept the default values:
    sam init --name "ws-serverless-patterns" --location "https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/76bc5278-3f38-46e8-b306-f0bfda551f5a/module2/sam-python/sam-cookiecutter-2023-11-03.zip"

After SAM initialization finishes, navigate to the workshop code directory:
    cd ws-serverless-patterns

Delete the default samconfig.toml file
    rm samconfig.toml

Navigate to users directory
    cd ./users

<!-- Create a Python virtual environment (recommended) -->
# Read more about Python Environment and why it is recommended here: 
# https://csguide.cs.princeton.edu/software/virtualenv#:~:text=Virtual%20environments%20let%20you%20have,and%20when%20they%20are%20upgraded.

When you work on multiple Python projects, creating virtual Python environments are a best practice to isolate project dependencies. In this workshop, we will show you how to include libraries for your Lambda functions, so creating a virtual environment is a recommended first step.

0. List default dependencies:
    pip freeze

This should produce a rather long list of libraries. You don't want those cluttering your project.

1.Create a new virtual environment:
    python -m venv venv
Python -m uses the 'venv' module to create a virtual environment called 'venv'.
# Got the below and followed the instruction to resolve it
    wsl@LAPTOP-400N4T7F:~/chuks-project-directory/Serverless-Pattern/Module-2/ws-serverless-patterns/users$ python3 -m venv venv
    The virtual environment was not created successfully because ensurepip is not
    available.  On Debian/Ubuntu systems, you need to install the python3-venv
    package using the following command.

        sudo apt update
        sudo apt upgrade
        apt install python3.10-venv

2.Activate the virtual environment:
    source venv/bin/activate

3. List default dependencies:
    pip freeze
In a new virtual env, you should see (venv) in the command prompt and zero dependencies.

# CI/CD Pipelines & CodeCommit
    Now would be a good time to add the project to a source control repository. In the interest of time, we're going to skip that step. After completing Module 2, you can choose to learn about source control integration and pipelines in CI/CD Pipelines.


Congratulations! Your project is set up and you are ready to move on!

<!-- 1 Define a Users table -->
In your IDE, open the ws-serverless-patterns/users directory
Open template.yaml in the editor.
Replace the contents of the file with following to define a DynamoDB table:

####

    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: >
    SAM Template for Serverless Patterns v1 - Data store

    # Globals:

    Resources:
    UsersTable:
        Type: AWS::DynamoDB::Table
        Properties:
            TableName: !Sub  ${AWS::StackName}-Users
            AttributeDefinitions:
            - AttributeName: userid
                AttributeType: S
            KeySchema:
            - AttributeName: userid
                KeyType: HASH
            BillingMode: PAY_PER_REQUEST

    Outputs:
    UsersTable:
        Description: DynamoDB Users table
        Value: !Ref UsersTable

###

<!-- Deploy the template -->
cd ~/path_to_project/ws-serverless-patterns/users
sam build
sam deploy --guided --stack-name ws-serverless-patterns-users

<!-- 2 - Add Business Logic -->

1) Add Lambda Function to template: replace the template content with the below

###
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Description: >
    SAM Template for Serverless Patterns - v2 Lambda function

    Globals:
    Function:
        Runtime: python3.9
        MemorySize: 128
        Timeout: 100
        Tracing: Active

    Resources:
    UsersTable:
        Type: AWS::DynamoDB::Table
        Properties:
        TableName: !Sub  ${AWS::StackName}-Users
        AttributeDefinitions:
            - AttributeName: userid
            AttributeType: S
        KeySchema:
            - AttributeName: userid
            KeyType: HASH
        BillingMode: PAY_PER_REQUEST

    UsersFunction:
        Type: AWS::Serverless::Function
        Properties:
        Handler: src/api/users.lambda_handler
        Description: Handler for all users related operations
        Environment:
            Variables:
            USERS_TABLE: !Ref UsersTable
        Policies:
            - DynamoDBCrudPolicy:
                TableName: !Ref UsersTable
        Tags:
            Stack: !Sub "${AWS::StackName}"

    Outputs:
    UsersTable:
        Description: DynamoDB Users table
        Value: !Ref UsersTable

    UsersFunction:
        Description: "Lambda function used to perform actions on the users data"
        Value: !Ref UsersFunction
###

2. Update the lambda in src/api/user.py
###

import json
import uuid
import os
import boto3
from datetime import datetime

# Prepare DynamoDB client
USERS_TABLE = os.getenv('USERS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(USERS_TABLE)

def lambda_handler(event, context):
    route_key = f"{event['httpMethod']} {event['resource']}"

    # Set default response, override with data from DynamoDB if any
    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
        }

    try:
        # Get a list of all Users
        if route_key == 'GET /users':
            ddb_response = ddbTable.scan(Select='ALL_ATTRIBUTES')
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200

        # CRUD operations for a single User
       
        # Read a user by ID
        if route_key == 'GET /users/{userid}':
            # get data from the database
            ddb_response = ddbTable.get_item(
                Key={'userid': event['pathParameters']['userid']}
            )
            # return single item instead of full DynamoDB response
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        
        # Delete a user by ID
        if route_key == 'DELETE /users/{userid}':
            # delete item in the database
            ddbTable.delete_item(
                Key={'userid': event['pathParameters']['userid']}
            )
            response_body = {}
            status_code = 200
        
        # Create a new user 
        if route_key == 'POST /users':
            request_json = json.loads(event['body'])
            request_json['timestamp'] = datetime.now().isoformat()
            # generate unique id if it isn't present in the request
            if 'userid' not in request_json:
                request_json['userid'] = str(uuid.uuid1())
            # update the database
            ddbTable.put_item(
                Item=request_json
            )
            response_body = request_json
            status_code = 200

        # Update a specific user by ID
        if route_key == 'PUT /users/{userid}':
            # update item in the database
            request_json = json.loads(event['body'])
            request_json['timestamp'] = datetime.now().isoformat()
            request_json['userid'] = event['pathParameters']['userid']
            # update the database
            ddbTable.put_item(
                Item=request_json
            )
            response_body = request_json
            status_code = 200
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body),
        'headers': headers
    }

###

3. Update the Python dependency list
Open ws-serverless-patterns/users/requirements.txt and copy/paste in the following dependencies:
    datetime
    boto3
    python-jose

4.Build and deploy
    sam build && sam deploy

# Error with deploy?
# If you receive an error saying, 'Error: Cannot use both --resolve-s3 and --s3-bucket parameters in non-guided deployments', you can resolve by running sam deploy --guided # or comment out --resolve-s3 in samconfig.toml.


<!-- GO ReadMe-Test-Function.md  -->
Go to the file above to test your lambda function locally

<!-- Connect function to API Gateway -->
Edit the SAM template.yaml, by replacing it's content with the following cfn:

##
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v3 Connect API

Globals:
  Function:
    Runtime: python3.9
    MemorySize: 128
    Timeout: 100
    Tracing: Active
Resources:
    UsersTable:
        Type: AWS::DynamoDB::Table
        Properties:
        TableName: !Sub  ${AWS::StackName}-Users
        AttributeDefinitions:
            - AttributeName: userid
            AttributeType: S
        KeySchema:
            - AttributeName: userid
            KeyType: HASH
        BillingMode: PAY_PER_REQUEST

    UsersFunction:
        Type: AWS::Serverless::Function
        Properties:
        Handler: src/api/users.lambda_handler
        Description: Handler for all users related operations
        Environment:
            Variables:
            USERS_TABLE: !Ref UsersTable
        Policies:
            - DynamoDBCrudPolicy:
                TableName: !Ref UsersTable
        Tags:
            Stack: !Sub "${AWS::StackName}"
        Events:
            GetUsersEvent:
            Type: Api
            Properties:
                Path: /users
                Method: get
                RestApiId: !Ref RestAPI
            PutUserEvent:
            Type: Api
            Properties:
                Path: /users
                Method: post
                RestApiId: !Ref RestAPI
            UpdateUserEvent:
            Type: Api
            Properties:
                Path: /users/{userid}
                Method: put
                RestApiId: !Ref RestAPI
            GetUserEvent:
            Type: Api
            Properties:
                Path: /users/{userid}
                Method: get
                RestApiId: !Ref RestAPI
            DeleteUserEvent:
            Type: Api
            Properties:
                Path: /users/{userid}
                Method: delete
                RestApiId: !Ref RestAPI

    RestAPI:
        Type: AWS::Serverless::Api
        Properties:
        StageName: Prod
        TracingEnabled: true
        Tags:
            Name: !Sub "${AWS::StackName}-API"
            Stack: !Sub "${AWS::StackName}"      

Outputs:
    UsersTable:
        Description: DynamoDB Users table
        Value: !Ref UsersTable

    UsersFunction:
        Description: "Lambda function used to perform actions on the users’ data"
        Value: !Ref UsersFunction

    APIEndpoint:
        Description: "API Gateway endpoint URL"
        Value: !Sub "https://${RestAPI}.execute-api.${AWS::Region}.amazonaws.com/Prod"
##

<!-- Build and Deploy -->
Generally, you always need to build before you deploy, so run them both together:

    sam build && sam deploy

<!-- Deploy Checkpoint -->
After the deploy finishes, verify that your API works...
Take note of the API Endpoint value from the build. Use it to validate the API works:

    curl <API Endpoint>/users

You should see an empty response with [] is this is the first deployment of the stack 
or it returns the users in the db if you have completed the previous steps in this module
<!-- 3.1 - Create User Pool -->
For the API authentication and authorization, you will use a Lambda Authorizer function in API Gateway. 
A Cognito User Pool Cognito User Pool  will be used for the user directory.
<!-- Set up Cognito for Lambda Authorizer -->
You will create a Cognito user pool to track users. The pool, a user directory, will require two attributes for each user: name & email. The email address will be used as a username and will be automatically verified.

You will also create a client and domain for the User Pool, and a group to specify admin-level users. The name of the administrative group will be added to the Parameters section of the stack template so you can override the default value if needed.

The Cognito login URL and AWS CLI command stub will be added to the stack output for later reference.

<!-- Update template.yaml -->
Paste the following template into template.yaml by replacing all of its content:

##

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v4 - Cognito

Globals:
  Function:
    Runtime: python3.9
    MemorySize: 128
    Timeout: 100
    Tracing: Active

Parameters:
  UserPoolAdminGroupName:
    Description: User pool group name for API administrators 
    Type: String
    Default: apiAdmins

Resources:
  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub  ${AWS::StackName}-Users
      AttributeDefinitions:
        - AttributeName: userid
          AttributeType: S
      KeySchema:
        - AttributeName: userid
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST

  UsersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/users.lambda_handler
      Description: Handler for all users related operations
      Environment:
        Variables:
          USERS_TABLE: !Ref UsersTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable
      Tags:
        Stack: !Sub "${AWS::StackName}"
      Events:
        GetUsersEvent:
          Type: Api
          Properties:
            Path: /users
            Method: get
            RestApiId: !Ref RestAPI
        PutUserEvent:
          Type: Api
          Properties:
            Path: /users
            Method: post
            RestApiId: !Ref RestAPI
        UpdateUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: put
            RestApiId: !Ref RestAPI
        GetUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: get
            RestApiId: !Ref RestAPI
        DeleteUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: delete
            RestApiId: !Ref RestAPI

  RestAPI:
    Type: AWS::Serverless::Api
    Properties:
      StageName: Prod
      TracingEnabled: true
      Tags:
        Name: !Sub "${AWS::StackName}-API"
        Stack: !Sub "${AWS::StackName}"      

  UserPool:
    Type: AWS::Cognito::UserPool
    Properties: 
      UserPoolName: !Sub ${AWS::StackName}-UserPool
      AdminCreateUserConfig: 
        AllowAdminCreateUserOnly: false
      AutoVerifiedAttributes: 
        - email
      Schema: 
        - Name: name
          AttributeDataType: String
          Mutable: true
          Required: true
        - Name: email
          AttributeDataType: String
          Mutable: true
          Required: true
      UsernameAttributes: 
        - email
      UserPoolTags:
          Key: Name
          Value: !Sub ${AWS::StackName} User Pool

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties: 
      ClientName: 
        !Sub ${AWS::StackName}UserPoolClient
      ExplicitAuthFlows: 
        - ALLOW_USER_PASSWORD_AUTH
        - ALLOW_USER_SRP_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH
      GenerateSecret: false
      PreventUserExistenceErrors: ENABLED
      RefreshTokenValidity: 30
      SupportedIdentityProviders: 
        - COGNITO
      UserPoolId: !Ref UserPool
      AllowedOAuthFlowsUserPoolClient: true
      AllowedOAuthFlows:
        - 'code'
      AllowedOAuthScopes:
        - 'email'
        - 'openid'
      CallbackURLs:
        - 'http://localhost'

  UserPoolDomain:
    Type: AWS::Cognito::UserPoolDomain
    Properties: 
      Domain: !Ref UserPoolClient
      UserPoolId: !Ref UserPool

  ApiAdministratorsUserPoolGroup:
    Type: AWS::Cognito::UserPoolGroup
    Properties:
      Description: User group for API Administrators
      GroupName: !Ref UserPoolAdminGroupName
      Precedence: 0
      UserPoolId: !Ref UserPool

Outputs:
  UsersTable:
    Description: DynamoDB Users table
    Value: !Ref UsersTable

  UsersFunction:
    Description: "Lambda function used to perform actions on the users data"
    Value: !Ref UsersFunction

  APIEndpoint:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${RestAPI}.execute-api.${AWS::Region}.amazonaws.com/Prod"

  UserPool:
    Description: Cognito User Pool ID
    Value: !Ref UserPool

  UserPoolClient:
    Description: Cognito User Pool Application Client ID
    Value: !Ref UserPoolClient

  UserPoolAdminGroupName:
    Description: User Pool group name for API administrators
    Value: !Ref UserPoolAdminGroupName
  
  CognitoLoginURL:
    Description: Cognito User Pool Application Client Hosted Login UI URL
    Value: !Sub 'https://${UserPoolClient}.auth.${AWS::Region}.amazoncognito.com/login?client_id=${UserPoolClient}&response_type=code&redirect_uri=http://localhost'

  CognitoAuthCommand:
    Description: AWS CLI command for Amazon Cognito User Pool authentication
    Value: !Sub 'aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id ${UserPoolClient} --auth-parameters USERNAME=<user@example.com>,PASSWORD=<password>'


##

<!-- New template Resources -->

Look at the updated SAM template.yaml, you will see these new resources:

UserPool - an AWS::Cognito::UserPool resource, configured with name and email as username
UserPoolClient - an entity within a pool with permission to call unauthenticated API operations
UserPoolDomain - built in domain (example.com) for authentication
ApiAdministratorsUserPoolGroup - user group for API Administrators

<!-- Template Parameters -->

One new twist in this version of the template is a Parameters section. Parameters add a new setting that you will be prompted to enter a value for UserPoolAdminGroupName.
In this template it doesn't bcs a default has been set for the parameter

<!-- Deploy Checkpoint - Cognito user pool -->
    
    sam build && sam deploy

<!-- New Outputs -->

Stack outputs now include Cognito outputs: user pool, client, administrative group, login URL, and authentication CLI commands.

Take note of the CognitoLoginURL so that you can test authentication.

<!-- Cognito user registration -->
To explore the Users functionality, you need to create a user!

Paste the CognitoLoginURL into a new browser tab.
Choose the Sign up link and complete the form as follows:
For Email, enter an email you can access. A verification code will be sent to this email and is needed to confirm your account.
For Password, choose a password you will remember. You will need this password when authenticating.
Choose Sign up.
Enter the verification code from the email.
Ignore the browser error (site can not be reached error) after validation.

Congratulations!
You have a working account! Verify your new user in the Cognito console . Look for your account in the User pool list.

# NB: 3rd Party Tools & Identity Tokens
If you use command line or third-party tools, such as Postman, to test APIs, you'll need an Identity Token in the request "Authorization" header.

One option is to authenticate via the AWS CLI to get a token. See the deploy outputs for CognitoAuthCommand. After logging in, you may use the IdToken value in the command output for further testing.

<!-- 3.2 - Secure the API -->
In the last section, you leveraged Amazon Cognito for user sign-up and sign-on.

Cognito is obviously not the only identity provider (IdP). So, this section will show you how to set up an authorizer function which can be quickly modified to enable any OpenID Connect (OIDC) compliant IdP to provide authentication and authorization for your API.

To do this, you will create a custom Lambda authorizer function (authorizer.py) that uses JWT-based authorization and dynamically generates security policies for the API. This approach can be used for 3rd party IdPs - Okta, Ping, Auth0, and others, with minimal changes.

The authorizer code is based on an API Gateway Lambda Authorizer blueprint and implements JWT decoding and validation based on a Cognito code sample provided by AWS Premium Support. See the Additional Resources section for more information.

When invoked, the authorizer function will validate the token in the API request and extract the principal ID. The function will then use the principal ID (a GUID in this case) to restrict access to the resources specific to that user. (In complex cases, a policy could be created to also allow access to shared/group resources, but that is beyond the scope of this workshop.)

The authorizer also checks the principal ID is a member of the Cognito user pool group apiAdmins.

If the user is in the admin group, the authorizer includes additional policy statements to allow the user to perform actions on resources that they do not own. This special admin group name, the user pool ID, and application client ID are all passed to the authorizer using environment variables for both flexibility and security.

Whew! That's a lot to take in, so here is a summary:

Create an authorizer function
Add it to the SAM resources
Deploy & Test authorized access to your API!

<!-- Create an Authorizer function for User access control (authorizer.py) -->
In the src/api/ folder, create a new file called authorizer.py and open it in the editor.

Paste the following code into authorizer.py and make sure to update default values in the lines 144-154 with your values :

Source for authorizer function - src/api/authorizer.py

##
import os
import re
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

# *** Section 1 : base setup and token validation helper function
is_cold_start = True
keys = {}
user_pool_id = os.getenv('USER_POOL_ID', None)
app_client_id = os.getenv('APPLICATION_CLIENT_ID', None)
admin_group_name = os.getenv('ADMIN_GROUP_NAME', None)


def validate_token(token, region):
    global keys, is_cold_start, user_pool_id, app_client_id
    if is_cold_start:
        # KEYS_URL -- REPLACE WHEN CHANGING IDENTITY PROVIDER!!
        keys_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        with urllib.request.urlopen(keys_url) as f:
            response = f.read()
        keys = json.loads(response.decode('utf-8'))['keys']
        is_cold_start = False

    # get the kid from the headers prior to verification
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        print('Public key not found in jwks.json')
        return False
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        print('Signature verification failed')
        return False
    print('Signature successfully verified')
    # since verification succeeded, you can now safely use the unverified claims
    claims = jwt.get_unverified_claims(token)

    # Additionally you can verify the token expiration
    if time.time() > claims['exp']:
        print('Token is expired')
        return False
    # and the Audience  (use claims['client_id'] if verifying an access token)
    if claims['aud'] != app_client_id:
        print('Token was not issued for this audience')
        return False
    decoded_jwt = jwt.decode(token, key=keys[key_index], audience=app_client_id)
    return decoded_jwt


def lambda_handler(event, context):
    global admin_group_name
    tmp = event['methodArn'].split(':')
    api_gateway_arn_tmp = tmp[5].split('/')
    region = tmp[3]
    aws_account_id = tmp[4]
    # validate the incoming token
    validated_decoded_token = validate_token(event['authorizationToken'], region)
    if not validated_decoded_token:
        raise Exception('Unauthorized')
    principal_id = validated_decoded_token['sub']
    # initialize the policy
    policy = AuthPolicy(principal_id, aws_account_id)
    policy.restApiId = api_gateway_arn_tmp[0]
    policy.region = region
    policy.stage = api_gateway_arn_tmp[1]

    # *** Section 2 : authorization rules
    # Allow all public resources/methods explicitly

    # Add user specific resources/methods
    policy.allow_method(HttpVerb.GET, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.PUT, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.DELETE, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.GET, f"/users/{principal_id}/*")
    policy.allow_method(HttpVerb.PUT, f"/users/{principal_id}/*")
    policy.allow_method(HttpVerb.DELETE, f"/users/{principal_id}/*")

    # Look for admin group in Cognito groups
    # Assumption: admin group always has higher precedence
    if 'cognito:groups' in validated_decoded_token and validated_decoded_token['cognito:groups'][0] == admin_group_name:
        # add administrative privileges
        policy.allow_method(HttpVerb.GET, "users")
        policy.allow_method(HttpVerb.GET, "users/*")
        policy.allow_method(HttpVerb.DELETE, "users")
        policy.allow_method(HttpVerb.DELETE, "users/*")
        policy.allow_method(HttpVerb.POST, "users")
        policy.allow_method(HttpVerb.PUT, "users/*")

    # Finally, build the policy
    auth_response = policy.build()
    return auth_response



# *** Section 3 : authorization policy helper classes
class HttpVerb:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    ALL = "*"


class AuthPolicy(object):
    awsAccountId = ""
    """The AWS account id the policy will be generated for. This is used to create the method ARNs."""
    principalId = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    version = "2012-10-17"
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    pathRegex = "^[/.a-zA-Z0-9-\*]+$"
    """The regular expression used to validate resource paths for the policy"""

    """these are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.
    the build method processes these lists and generates the appropriate
    statements for the final policy"""
    allowMethods = []
    denyMethods = []

    restApiId = "<<restApiId>>"
    """ Replace the placeholder value with a default API Gateway API id to be used in the policy. 
    Beware of using '*' since it will not simply mean any API Gateway API id, because stars will greedily expand over '/' or other separators. 
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    region = "<<region>>"
    """ Replace the placeholder value with a default region to be used in the policy. 
    Beware of using '*' since it will not simply mean any region, because stars will greedily expand over '/' or other separators. 
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    stage = "<<stage>>"
    """ Replace the placeholder value with a default stage to be used in the policy. 
    Beware of using '*' since it will not simply mean any stage, because stars will greedily expand over '/' or other separators. 
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    def __init__(self, principal, aws_account_id):
        self.awsAccountId = aws_account_id
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _add_method(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resource_pattern = re.compile(self.pathRegex)
        if not resource_pattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resource_arn = ("arn:aws:execute-api:" +
                        self.region + ":" +
                        self.awsAccountId + ":" +
                        self.restApiId + "/" +
                        self.stage + "/" +
                        verb + "/" +
                        resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })

    def _get_empty_statement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement

    def _get_statement_for_effect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._get_empty_statement(effect)

            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditional_statement = self._get_empty_statement(effect)
                    conditional_statement['Resource'].append(curMethod['resourceArn'])
                    conditional_statement['Condition'] = curMethod['conditions']
                    statements.append(conditional_statement)

            statements.append(statement)

        return statements

    def allow_all_methods(self):
        """Adds a '*' allow to the policy to authorize access to all methods of an API"""
        self._add_method("Allow", HttpVerb.ALL, "*", [])

    def deny_all_methods(self):
        """Adds a '*' allow to the policy to deny access to all methods of an API"""
        self._add_method("Deny", HttpVerb.ALL, "*", [])

    def allow_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._add_method("Allow", verb, resource, [])

    def deny_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._add_method("Deny", verb, resource, [])

    def allow_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Allow", verb, resource, conditions)

    def deny_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
                (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId': self.principalId,
            'policyDocument': {
                'Version': self.version,
                'Statement': []
            }
        }

        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Allow", self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Deny", self.denyMethods))

        return policy


##

<!-- What's happening in the lambda authorizer? -->
Wow. That's a lot of code in authorizer.py!?!

You're right. It is a lot of code, but we can simplify the explanation by breaking the code into three sections:

Section 1 (9-63) - mostly boilerplate code to validate the JWT token; except line #21 which specifies the keys_url for your IdP
Section 2 (66-107) - code that matters; your authorization rules are here!
Section 3 (111-276) - helper code to make security policy generation easier

<!-- Update the SAM template -->
Paste the following configuration into template.yaml to add an Auth property to the RestAPI, create an AuthorizerFunction resource, and configure a related LogGroup resource.

##

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v5 - JWT Authorizer

Globals:
  Function:
    Runtime: python3.9
    MemorySize: 128
    Timeout: 100
    Tracing: Active

Parameters:
  UserPoolAdminGroupName:
    Description: User pool group name for API administrators 
    Type: String
    Default: apiAdmins

Resources:
  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub  ${AWS::StackName}-Users
      AttributeDefinitions:
        - AttributeName: userid
          AttributeType: S
      KeySchema:
        - AttributeName: userid
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST

  UsersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/users.lambda_handler
      Description: Handler for all users related operations
      Environment:
        Variables:
          USERS_TABLE: !Ref UsersTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable
      Tags:
        Stack: !Sub "${AWS::StackName}"
      Events:
        GetUsersEvent:
          Type: Api
          Properties:
            Path: /users
            Method: get
            RestApiId: !Ref RestAPI
        PutUserEvent:
          Type: Api
          Properties:
            Path: /users
            Method: post
            RestApiId: !Ref RestAPI
        UpdateUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: put
            RestApiId: !Ref RestAPI
        GetUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: get
            RestApiId: !Ref RestAPI
        DeleteUserEvent:
          Type: Api
          Properties:
            Path: /users/{userid}
            Method: delete
            RestApiId: !Ref RestAPI

  RestAPI:
    Type: AWS::Serverless::Api
    Properties:
      StageName: Prod
      TracingEnabled: true
      Tags:
        Name: !Sub "${AWS::StackName}-API"
        Stack: !Sub "${AWS::StackName}"      
      Auth:
        DefaultAuthorizer: LambdaTokenAuthorizer
        Authorizers:
          LambdaTokenAuthorizer:
            FunctionArn: !GetAtt AuthorizerFunction.Arn
            Identity:
              Headers:
                - Authorization

  UserPool:
    Type: AWS::Cognito::UserPool
    Properties: 
      UserPoolName: !Sub ${AWS::StackName}-UserPool
      AdminCreateUserConfig: 
        AllowAdminCreateUserOnly: false
      AutoVerifiedAttributes: 
        - email
      Schema: 
        - Name: name
          AttributeDataType: String
          Mutable: true
          Required: true
        - Name: email
          AttributeDataType: String
          Mutable: true
          Required: true
      UsernameAttributes: 
        - email
      UserPoolTags:
          Key: Name
          Value: !Sub ${AWS::StackName} User Pool

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties: 
      ClientName: 
        !Sub ${AWS::StackName}UserPoolClient
      ExplicitAuthFlows: 
        - ALLOW_USER_PASSWORD_AUTH
        - ALLOW_USER_SRP_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH
      GenerateSecret: false
      PreventUserExistenceErrors: ENABLED
      RefreshTokenValidity: 30
      SupportedIdentityProviders: 
        - COGNITO
      UserPoolId: !Ref UserPool
      AllowedOAuthFlowsUserPoolClient: true
      AllowedOAuthFlows:
        - 'code'
      AllowedOAuthScopes:
        - 'email'
        - 'openid'
      CallbackURLs:
        - 'http://localhost'

  UserPoolDomain:
    Type: AWS::Cognito::UserPoolDomain
    Properties: 
      Domain: !Ref UserPoolClient
      UserPoolId: !Ref UserPool

  ApiAdministratorsUserPoolGroup:
    Type: AWS::Cognito::UserPoolGroup
    Properties:
      Description: User group for API Administrators
      GroupName: !Ref UserPoolAdminGroupName
      Precedence: 0
      UserPoolId: !Ref UserPool

  AuthorizerFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/api/authorizer.lambda_handler
      Description: Handler for Lambda authorizer
      Environment:
        Variables:
          USER_POOL_ID: !Ref UserPool
          APPLICATION_CLIENT_ID: !Ref UserPoolClient
          ADMIN_GROUP_NAME: !Ref UserPoolAdminGroupName
      Tags:
        Stack: !Sub "${AWS::StackName}"

Outputs:
  UsersTable:
    Description: DynamoDB Users table
    Value: !Ref UsersTable

  UsersFunction:
    Description: "Lambda function used to perform actions on the users data"
    Value: !Ref UsersFunction

  APIEndpoint:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${RestAPI}.execute-api.${AWS::Region}.amazonaws.com/Prod"

  UserPool:
    Description: Cognito User Pool ID
    Value: !Ref UserPool

  UserPoolClient:
    Description: Cognito User Pool Application Client ID
    Value: !Ref UserPoolClient

  UserPoolAdminGroupName:
    Description: User Pool group name for API administrators
    Value: !Ref UserPoolAdminGroupName
  
  CognitoLoginURL:
    Description: Cognito User Pool Application Client Hosted Login UI URL
    Value: !Sub 'https://${UserPoolClient}.auth.${AWS::Region}.amazoncognito.com/login?client_id=${UserPoolClient}&response_type=code&redirect_uri=http://localhost'

  CognitoAuthCommand:
    Description: AWS CLI command for Amazon Cognito User Pool authentication
    Value: !Sub 'aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id ${UserPoolClient} --auth-parameters USERNAME=<username>,PASSWORD=<password>'


##


<!-- What changed in template.yaml? -->
First, there is a new AuthorizerFunction resource to create the authorizer.py function.
The function type is a SAM resource AWS::Serverless::Function  which automatically creates not only the Lambda function, but also an Identity and Access Management (IAM) execution role and event source mappings to trigger the function.

Note - the Handler property has a convention of: <path-to-function>/<function-file-name-without-suffix>.<handler_method_name>

Lines 8,9, and 10 make environmental variables available to the function with the Amazon Cognito User Pool and Application Client IDs, and the name of the API administrative users' group in Cognito

Next, LambdaTokenAuthorizer is added in an Auth property for the RestAPI resource.
This connects the LambdaTokenAuthorizer to secure the API. The Authorizer function is specified by the ARN. Another intrinsic CloudFormation function, !GetATT, looks up the ARN for the just created AuthorizerFunction.

<!-- Deploy Checkpoint - Lambda Authorizer -->
    sam build && sam deploy

<!-- 3.3 - Verify Authorization -->
Next, you will authenticate as an administrator and verify your ability to view other users.

In the IDE terminal, run the following command, replacing <API Endpoint> with the value of APIEndpoint from the previous section:

    curl <API Endpoint>/users

You will see a response message that you are Unauthorized:

    {"message":"Unauthorized"}

# Step 1 - Get an Identity Token (IdToken)
Copy the CognitoAuthCommand command from the stack output
Replace USERNAME (your email address) and PASSWORD with values when you created your account.
That command should produce an AccessToken, RefreshToken, and IdToken under "Authenticated" key in a json output.
# Store the IdToken in an environment variable so that it's easy to re-use.
Copy the IdToken value from the output, taking care to select the entire token.:
Run this command to create an environment variable: export ID_TOKEN="<PASTE TOKEN HERE>"
Test by running echo $ID_TOKEN 

Now try the API request again to get the list of users, using the identity token as the Authorization header value:

curl <API_Endpoint>/users -H "Authorization:$ID_TOKEN"

This time you should see the message: “User is not authorized to access this resource".

Why?!? That's our fault. We told you to ask for a list of users, but you do not have permission to access other people's data. Regular users can only access their own data. You are currently just a regular user.

To get your own info, you need to know your principal ID. The principal ID is created by Cognito and is not your userid.

To find get your principal ID, you need to decode and extract it from the JWT token:

Navigate to https://jwt.io/ 
Paste in the IdToken value and choose to decode it
Take note of the sub field in the payload data
sub - is the "subject claim" which identifies the principal that is the subject of the JWT.
SPOILER ALERT: If request your data based on your principal ID now, there won't be any - {}! The Users table has no items for that principal ID at this time.

Go ahead and try getting data for your principal ID:

curl <API Endpoint>/users/<sub-value> -H "Authorization:$ID_TOKEN"

# Step 2 - Add your data via the API
Use the HTTP PUT method to add your user data to the system:

curl --location --request PUT 'https://pq6e1uotni.execute-api.ca-central-1.amazonaws.com/Prod/users/<SUB-VALUE>' \
     --data-raw '{"name": "Rackel"}' \
     --header "Authorization: $ID_TOKEN" \
     --header "Content-Type: application/json" \


If successful, you should receive confirmation similar to the following: {"name": "My name is Tim", "timestamp": "2022-12-02T04:20:34.832362", "userid": "5152984a-1a10-47fe-bf38-4fde8339ba64"}

Afetrward, you should receive the same result running the command to GET /users/ :

    curl <API Endpoint>/users/<sub-value> -H "Authorization:$ID_TOKEN"

Step 3 - Add your userid to the administrative group
To access other user's data, you need to add yourself to the administrators group.

<!-- Navigate to the Cognito Management Console  -->
Choose the user pool created for this workshop.
In the Users tab, choose your user ID, then scroll down to the Group memberships section.
Choose Add user to a group.
Select the Admin group (apiAdmins) and choose Add.
<!-- Step 4 - Verify your administrative access -->
1. Obtain a new token using the steps in Step 1 - Get an identity token.
2. Make another requests to the users endpoint with the following command:

    curl <API Endpoint>/users -H "Authorization:<IdToken value>"

This time you should see a list of users!

IAM policy generated by the Lambda Authorizer could be cached by API Gateway.

You may need to wait to gain access (default timeout is five minutes).

Or, you can repeat Step 1 to get a new ID_TOKEN.

<!-- 4 - Unit Test -->
    GO ReadMe-Unit-Test-Function.md

<!-- 5 - Integration Test -->
  GO ReadMe-Integration-Test-Function.md

<!-- 6 - Observe the App -->

  Go to ReadMe-Observability.md

<!-- 6.1 - Set Alarms-->

  Go to ReadMe-Alarms.md

<!-- 6.2 - Display a Dashboard -->

  Go to ReadMe-Dashboard.md

<!-- Module 2 completed -->
Before you delete resources... 

Before you delete the workshop, we recommend reviewing the stack in the CloudFormation console so you can see the value of SAM templates:

Open the CloudFormation Console  and choose Stacks from the navigation pane.

Find your ws-serverless-patterns-users stack.

Take a look at Stack info, Events, Resources, Outputs, and Template.

Choose "View processed template" to transform the SAM template into CloudFormation JSON.

The SAM template is less than about 450 lines, but it expands to nearly a thousand lines of CloudFormation during the transform step! Switch back and forth between SAM and CloudFormation. Which one would you rather read and update?

<!-- Delete your stack? -->

STOP!!! Wait! Read me!
If you want to continue with another module or deep dive, skip this step and go to "Module 3 setup" below. You may need your stack!

<!-- If you are certain you do not want to continue... you can run the following command to delete the stack (accept default values when prompted): -->

  sam delete --stack-name ws-serverless-patterns-users

<!-- Module 3 setup -->

  Go to Readme-Setup.md

<!-- Module 3 tasks -->

  Go to ReadMe-Module-3.md
