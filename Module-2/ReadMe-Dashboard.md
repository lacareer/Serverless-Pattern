Alarms are great for notifying you when metrics are out of bounds, but they are one-offs and may not provide a holistic picture of your application's health and performance. What if you want to see all your application's important metrics in a single view?

Amazon CloudWatch dashboards are customizable home pages in the CloudWatch console that you can use to monitor your resources in a single view, even those resources that are spread across different Regions. You can use CloudWatch dashboards to create customized views of the metrics and alarms for your AWS resources.

In this section, you will create an Amazon CloudWatch Dashboard which displays metrics from the application's components.

<!-- Add observability resources -->
Paste the following into template.yaml to add an observability dashboard:

##
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v8 - Observability - Dashboard

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

  AlarmsTopic:
    Type: AWS::SNS::Topic
    Properties:
      Tags:
        - Key: "Stack" 
          Value: !Sub "${AWS::StackName}"

  RestAPIErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: ApiName
          Value: !Ref RestAPI
      EvaluationPeriods: 1
      MetricName: 5XXError
      Namespace: AWS/ApiGateway
      Period: 60
      Statistic: Sum
      Threshold: 1.0

  AuthorizerFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: FunctionName
          Value: !Ref AuthorizerFunction
      EvaluationPeriods: 1
      MetricName: Errors
      Namespace: AWS/Lambda
      Period: 60
      Statistic: Sum
      Threshold: 1.0      

  AuthorizerFunctionThrottlingAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: FunctionName
          Value: !Ref AuthorizerFunction
      EvaluationPeriods: 1
      MetricName: Throttles
      Namespace: AWS/Lambda
      Period: 60
      Statistic: Sum
      Threshold: 1.0

  UsersFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: FunctionName
          Value: !Ref UsersFunction
      EvaluationPeriods: 1
      MetricName: Errors
      Namespace: AWS/Lambda
      Period: 60
      Statistic: Sum
      Threshold: 1.0

  UsersFunctionThrottlingAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: FunctionName
          Value: !Ref UsersFunction
      EvaluationPeriods: 1
      MetricName: Throttles
      Namespace: AWS/Lambda
      Period: 60
      Statistic: Sum
      Threshold: 1.0

  ApplicationDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: !Sub "${AWS::StackName}-dashboard"
      DashboardBody:
        Fn::Sub: >
          {
            "widgets": [
                {
                    "height": 6,
                    "width": 6,
                    "y": 6,
                    "x": 0,
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [ "AWS/Lambda", "Invocations", "FunctionName", "${UsersFunction}" ],
                            [ ".", "Errors", ".", "." ],
                            [ ".", "Throttles", ".", "." ],
                            [ ".", "Duration", ".", ".", { "stat": "Average" } ],
                            [ ".", "ConcurrentExecutions", ".", ".", { "stat": "Maximum" } ]
                        ],
                        "view": "timeSeries",
                        "region": "${AWS::Region}",
                        "stacked": false,
                        "title": "Users Lambda",
                        "period": 60,
                        "stat": "Sum"
                    }
                },
                {
                    "height": 6,
                    "width": 6,
                    "y": 6,
                    "x": 6,
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [ "AWS/Lambda", "Invocations", "FunctionName", "${AuthorizerFunction}" ],
                            [ ".", "Errors", ".", "." ],
                            [ ".", "Throttles", ".", "." ],
                            [ ".", "Duration", ".", ".", { "stat": "Average" } ],
                            [ ".", "ConcurrentExecutions", ".", ".", { "stat": "Maximum" } ]
                        ],
                        "view": "timeSeries",
                        "region": "${AWS::Region}",
                        "stacked": false,
                        "title": "Authorizer Lambda",
                        "period": 60,
                        "stat": "Sum"
                    }
                },
                {
                    "height": 6,
                    "width": 12,
                    "y": 0,
                    "x": 0,
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [ "AWS/ApiGateway", "4XXError", "ApiName", "${AWS::StackName}", { "yAxis": "right" } ],
                            [ ".", "5XXError", ".", ".", { "yAxis": "right" } ],
                            [ ".", "DataProcessed", ".", ".", { "yAxis": "left" } ],
                            [ ".", "Count", ".", ".", { "label": "Count", "yAxis": "right" } ],
                            [ ".", "IntegrationLatency", ".", ".", { "stat": "Average" } ],
                            [ ".", "Latency", ".", ".", { "stat": "Average" } ]
                        ],
                        "view": "timeSeries",
                        "stacked": false,
                        "region": "${AWS::Region}",
                        "period": 60,
                        "stat": "Sum",
                        "title": "API Gateway"
                    }
                }
            ]
          }

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

  AlarmsTopic:
    Description: "SNS Topic to be used for the alarms subscriptions"
    Value: !Ref AlarmsTopic

  DashboardURL:
    Description: "Dashboard URL"
    Value: !Sub "https://console.aws.amazon.com/cloudwatch/home?region=${AWS::Region}#dashboards:name=${ApplicationDashboard}"

##

<!-- What's changed in the template? -->
The updated template adds a CloudWatch dashboard resource and corresponding Dashboard URL.

<!-- Application dashboard -->
The template now has a new AWS::CloudWatch::Dashboard resource which will create an application dashboard in CloudWatch. The dashboard will include widgets for API Gateway and Lambda metrics. In a more sophisticated case, you might add additional business-specific metrics to the dashboard.

Tip: A good method to create dashboard definitions is building the dashboard with the AWS Management Console then exporting the JSON definition. You will still need to replace resource names in the definition with references to the resources in your template, but it's a quick way to get started!

In fact, creating the dashboard in the console is how we created the following dashboard definition. Note how the Lambda function names is replaced with ${UsersFunction} and ${AuthorizerFunction}, API name with ${RestAPI}, and AWS Region name with ${AWS::Region}. These values will be substituted into the dashboard with the actual values.

##
  ApplicationDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: !Sub "${AWS::StackName}-dashboard"
      DashboardBody:
        Fn::Sub: >
          {
            "widgets": [
                {
                    "height": 6,
                    "width": 12,
                    "y": 0,
                    "x": 0,
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [ "AWS/ApiGateway", "4xx", "ApiId", "${RestAPI}", { "yAxis": "right" } ],
                            [ ".", "5xx", ".", ".", { "yAxis": "right" } ],
                            [ ".", "DataProcessed", ".", ".", { "yAxis": "left" } ],
                            [ ".", "Count", ".", ".", { "label": "Count", "yAxis": "right" } ],
                            [ ".", "IntegrationLatency", ".", ".", { "stat": "Average" } ],
                            [ ".", "Latency", ".", ".", { "stat": "Average" } ]
                        ],
                        "view": "timeSeries",
                        "stacked": false,
                        "region": "${AWS::Region}",
                        "period": 60,
                        "stat": "Sum",
                        "title": "API Gateway"
                    }
                },
               
               ... two additional widgets ... omitted for brevity...
               ...
               ... Remember: you can find references to resources by name. 
               ... Go find the resource now in your template.yaml now!  

                }
            ]
          }
##

The resource type is a CloudWatch dashboard, with a layout and three widgets defined in a JSON array:

1. Widget #1 - API Gateway metrics

    Data fields include: 4XX and 5XX errors, number of requests, latency and integration latency, amount of data processed. We use two separate Y axis used by metrics for better visibility as their ranges of values differ. Note that ${RestAPI} is used in the definition to refer to the resource defined in the template.

2. Widget #2 - Users Lambda function metrics

    Data fields include: number of invocations, errors, throttles, average invocation duration and maximum number of concurrent executions. Note that ${UsersFunction} is used in the definition to refer to the resource defined in the same template.

3. Widget #3 - Authorizer Lambda function metrics

    Data fields include: number of invocations, errors, throttles, average invocation duration and maximum number of concurrent executions. Note ${AuthorizerFunction} used in the definition to refer to the resource defined in the same template.

<!-- Access Dashboard -->
For easier access to the dashboard, an Output with the dashboard URL is added to the stack:
##
  DashboardURL:
    Description: "Dashboard URL"
    Value: !Sub "https://console.aws.amazon.com/cloudwatch/home?region=${AWS::Region}#dashboards:name=${ApplicationDashboard}"
##

<!-- Deploy Checkpoint -->
Deploy the dashboard with the now familiar commands:

    sam build && sam deploy

Running the integration test suite should generate some activity. You can also set the time window to be 5 minutes so you start seeing data in the widgets.

<!-- For extra credit -->
1. Re-arrange the widgets to your liking.
2. Choose Actions, then View/edit source.
3. Review the source code and determine how to update your SAM application with the changes.
4. Update your template.yaml with the changes and re-deploy