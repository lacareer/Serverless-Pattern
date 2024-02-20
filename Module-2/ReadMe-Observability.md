Serverless applications are built from, and use, many services. Interactions between these components quickly becomes complex. Centralized logs and metric collection will help you detect, investigate, and remediate problems faster.

Observability is this ability to collect, monitor, act on, and analyze telemetry in your applications.

Each service has different metrics that matter. The relevant data not only varies by service, but you must also consider interactions between services. For example, measuring how quickly Lambda can process API Gateway requests, or how fast a function consumes messages in queue will help you optimize each service and improve how they work together.

A successful observability strategy captures metrics that help you make decisions.

In the next three sections, we will show you how to add the following observability features:

API Gateway access logging
SNS queue for alarm messaging
Alarms
API Gateway
Lambda Authorizer function
Business logic Lambda function
In this section, you will configure access and execution logging in Amazon API Gateway and configure an SNS queue for messaging.

<!-- Add observability resources -->
Paste the following template into template.yaml to add observability:

##

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v6 - Observability

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
      AccessLogSetting:
        DestinationArn: !GetAtt AccessLogs.Arn
        Format: '{ "requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "integrationStatus": $context.integrationStatus, "integrationLatency": $context.integrationLatency, "responseLength":"$context.responseLength" }'
      MethodSettings:
        - ResourcePath: "/*"
          LoggingLevel: INFO
          HttpMethod: "*"
          DataTraceEnabled: True

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

  ApiLoggingRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - apigateway.amazonaws.com
            Action: "sts:AssumeRole"
      Path: /
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

  ApiGatewayAccountLoggingSettings:
    Type: AWS::ApiGateway::Account
    Properties:
      CloudWatchRoleArn: !GetAtt ApiLoggingRole.Arn

  AccessLogs:
    Type: AWS::Logs::LogGroup
    DependsOn: ApiLoggingRole
    Properties:
      RetentionInDays: 30
      LogGroupName: !Sub "/${AWS::StackName}/APIAccessLogs"

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

<!-- What's changed in the template? -->
The updated template adds API Gateway access logging and an SNS queue for messaging that will be used for future for all alarms.
Each resource is configured to measure and monitor components in the system, and send you alerts when alarms have been triggered.

<!-- API Gateway access logging -->
First, the existing API Gateway logging permissions are set so the service can send logs to CloudWatch. The template creates an IAM role to be used for API logging, and then connects API Gateway to that newly created role to write API logs to Amazon CloudWatch Logs.

##

  ApiLoggingRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - apigateway.amazonaws.com
            Action: "sts:AssumeRole"
      Path: /
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

  ApiGatewayAccountLoggingSettings:
    Type: AWS::ApiGateway::Account
    Properties:
      CloudWatchRoleArn: !GetAtt ApiLoggingRole.Arn

##

<!-- Next, API Gateway access logs entries are set to stream in to CloudWatch logs: -->

Log retention defaults to indefinite retention, so logs never expire. Teams frequently ask how they can reduce the retention period, especially for events unlikely to be important after a short time. In the template, note how RetentionInDays is set to 30.

##
  AccessLogs:
    Type: AWS::Logs::LogGroup
    DependsOn: ApiLoggingRole
    Properties:
      RetentionInDays: 30
      LogGroupName: !Sub "/${AWS::StackName}/APIAccessLogs"
##

<!-- The following properties for the RestAPI resource enable API Gateway access and execution logging : -->

##
AccessLogSetting:
  DestinationArn: !GetAtt AccessLogs.Arn
  Format: '{ "requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "integrationStatus": $context.integrationStatus, "integrationLatency": $context.integrationLatency, "responseLength":"$context.responseLength" }'
MethodSettings:
  - ResourcePath: "/*"
    LoggingLevel: INFO
    HttpMethod: "*"
    DataTraceEnabled: True 
##

Look at how the DestinationArn property gets an ARN reference to the CloudWatch Logs log stream, which is defined in the previous code block. The template uses another intrinsic CloudFormation function called !GetAtt.

Format property includes many values of interest from the context object.
MethodSettings enables this logging for all resources and all methods in the API.

<!-- Deploy the updates -->
Deploy the changes by running:

    sam build && sam deploy

<!-- Observe logging -->
With the logging changes deployed, let's see the results by running the integration tests.

In you IDE, run the integration test:
    python3 -m pytest tests/integration -v 
    
## OR (Depending on your machine)

    python -m pytest tests/integration -v 


Navigate to CloudWatch Console .

Under Logs, choose Log groups.

Choose the Log group named ws-serverless-patterns/ApiAccessLogs.

Within the Log group, you will see streams containing the logged events from API Gateway. To see a log, choose a stream and view the contents. The log structure is exactly what you specified in the accessLogFormat property!

<!-- Observe tracing -->
In the CloudWatch console, choose Traces under X-Ray traces.
The Traces table lists the individual traces collected. Choosing a trace opens a Trace Map and the Segments Timeline. Explore the map and timeline to see how your request traveled through the application!