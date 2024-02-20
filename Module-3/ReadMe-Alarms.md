In this section, you will create Amazon CloudWatch metric alarms to monitor errors and increases in traffic.

A metric alarm watches a single CloudWatch metric, or the result of a math expression based on CloudWatch metrics. The alarm performs one or more actions based on the value of the metric, or the result of an expression, relative to a threshold over a number of time periods.

For your application, the action will publish messages to an Amazon SNS topic.

<!-- Add alarm resources -->
Paste the following configuration with alarm resources into template.yaml:

##

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
  SAM Template for Serverless Patterns v7 - Observability - Alarms

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

##

<!-- What's changed in the template? -->
The updated template adds an SNS topic and alarms for the API Gateway and Lambda functions.

* SNS topic for messaging for all alarms
* Alarms
* API Gateway
    - Lambda Authorizer function
    - Business logic Lambda function
    - Each alarm is configured to measure and monitor components in the system, and send you alerts when metrics exceed thresholds.

<!-- SNS Topic for Alarms -->
The first new resource is an AlarmsTopic which is a Simple Notification Service (SNS). This is a topic that the components will use to send notifications for triggered alarms. :

##
  AlarmsTopic:
    Type: AWS::SNS::Topic
    Properties:
      Tags:
        - Key: "Stack" 
          Value: !Sub "${AWS::StackName}"
##

<!-- The Outputs section includes a reference to the topic : -->

##
  AlarmsTopic:
    Description: "SNS Topic to be used for the alarms subscriptions"
    Value: !Ref AlarmsTopic
##

<!-- API Gateway alarms -->
In your production environments, you would likely create sophisticated alarm rules that would consider percentage of requests in error, affected subsystems, and other business KPI's.

In this workshop, any server error (HTTP 500) logged will trigger the alarm. CloudWatch will sum the errors over a period of 1 minute to determine the alarm status. Once the threshold is met, CloudWatch will publish a message to the RestAPIErrorsAlarm SNS Topic.
This template snippet will create an alarm that will send notification on every 5XX error.

##
 RestAPIErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      Dimensions:
        - Name: ApiName
          Value: !Ref RestAPI
      Namespace: AWS/ApiGateway
      MetricName: 5XXError
      Statistic: Sum
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Threshold: 1.0
      Period: 60
      EvaluationPeriods: 1
##

<!-- Line by line explanation of code... -->
Line    number	Description
1	    Name of the resource
2	    Type of the resource. AWS CloudFormation resource  that specifies an alarm and associates it with the specified metric
4-5	    Specifying actions to be performed when it transitions into ALARM state - send a message to the SNS topic created earlier
6-8	    Dimensions of the metric associated with the alarm: name of the API.
9-10	Namespace and metric name that defines metric associated with the alarm. 5XX errors by Amazon API Gateway.
11-13	Statistics of the metric (Sum) to be compared by the comparison operator (GreaterThanOrEqualToThreshold) to the threshold (1) to determine state of the alarm
14-15	Length of the period of time over which the statistics is applied and number of periods over which data is compared to the specified threshold while determining state of the alarm.

<!-- Lambda Authorizer alarms -->
Similar to the API Gateway alarm, errors in the Lambda Authorizer will send a notification to the topic:

##
  AuthorizerFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      Dimensions:
        - Name: FunctionName
          Value: !Ref AuthorizerFunction
      Namespace: AWS/Lambda
      MetricName: Errors
      Statistic: Sum
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Threshold: 1.0
      Period: 60
      EvaluationPeriods: 1
##

<!-- Line by line explanation of code... -->
Line    number	Description
1	    Name of the resource
2	    Type of the resource
4-5	    Specifying actions to be performed when it transitions into ALARM state: send a message to the SNS topic created earlier
6-8	    Dimensions of the metric associated with the alarm. Here it is the name of the Lambda Authorizer function. For more information, see CloudWatch - Concepts - Dimension 
9-10	Namespace and metric name that defines metric associated with the alarm. In this case, it is errors by AWS Lambda. For more information, see CloudWatch - Namespaces 
11-13	Statistics of the metric (Sum) to be compared by the comparison operator (GreaterThanOrEqualToThreshold) to the threshold (1) to determine state of the alarm
14-15	Length of the period of time over which the statistics is applied and number of periods over which data is compared to the specified threshold while determining state of the alarm.


<!-- Alarm for surge in traffic -->
To help identify surges in traffic, an alarm based on throttled invocations is added to the Lambda Authorizer. Throttling means a request is not handled by your function. Throttling can happen when a function receives a sudden burst in traffic and reaches the concurrency limits for your account:

<!-- Business logic Lambda alarms -->
Similarly to the authorizer, there is an alarm for Users function errors to send notification any time an error occurs during the last minute. :
##
  UsersFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      Dimensions:
        - Name: FunctionName
          Value: !Ref UsersFunction
      Namespace: AWS/Lambda
      MetricName: Errors
      Statistic: Sum
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Threshold: 1.0
      Period: 60
      EvaluationPeriods: 1
##
<!-- Line by line explanation of code... -->
Line    number	Description
1	    Name of the resource
2	    Type of the resource. CloudFormation resource  that specifies an alarm and associates it with the specified metric
4-5	    Specifying actions to be performed when it transitions into ALARM state - send a message to the SNS topic created earlier
6-8	    Dimensions of the metric associated with the alarm: Users Lambda function.
9-10	Namespace and metric name that defines metric associated with the alarm. In this case, it is errors by AWS Lambda.
11-13	Statistics of the metric (Sum) to be compared by the comparison operator (GreaterThanOrEqualToThreshold) to the threshold (1) to determine state of the alarm
14-15	Length of the period of time over which the statistics is applied and number of periods over which data is compared to the specified threshold while determining state of the alarm.


<!-- Lastly, a separate alarm resource UsersFunctionThrottlingAlarm will notify when Users Lambda function invocation is throttled : -->
##
  UsersFunctionThrottlingAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmActions:
        - !Ref AlarmsTopic
      Dimensions:
        - Name: FunctionName
          Value: !Ref UsersFunction
      Namespace: AWS/Lambda
      MetricName: Throttles
      Statistic: Sum
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Threshold: 1.0
      Period: 60
      EvaluationPeriods: 1
##

<!-- Line by line explanation of code... -->
Line    number	Description
1	    Name of the resource
2	    Type of the resource. CloudFormation resource  that specifies an alarm and associates it with the specified metric
4-5	    Specifying actions to be performed when it transitions into ALARM state - send message to the SNS topic created earlier
6-8	    Dimension of the metric - Users Lambda function
9-10	Namespace and metric name that defines metric associated with the alarm. In this case it is throttled by AWS Lambda.
11-13	Statistics of the metric (Sum) to be compared by the comparison operator (GreaterThanOrEqualToThreshold) to the threshold (1) to determine state of the alarm
14-15	Length of the period of time over which the statistics is applied and number of periods over which data is compared to the specified threshold while determining state of the alarm.

<!-- Tip -->
For more information on the AWS Lambda metrics, dimensions, and statistics to use for better insights, see Lambda - Monitoring Metrics (https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html).

<!-- Deploy Checkpoint -->
To deploy the changes, run the following commands:

    sam build && sam deploy

How do you know the alarms work?
First, you need to subscribe to the Alarm SNS topic. There are several ways to subscribe to alarms, but the easiest is with an email alert. Then, you manually set off some alarms!!

<!-- Subscribe your email to SNS topic via email -->
Go to the Amazon SNS Console .

Choose Topics from the navigation panel.

Choose the topic created during this workshop.

In the Subscriptions tab, choose Create subscription.

For Topic ARN, select the topic created in this workshop, if not already selected.

For Protocol, select Email.

For Endpoint, enter your email address.

Choose Create Subscription.

Go to the Simple Notification Service (SNS) Console 

Go to the list of Topics

Select the previously created workshop topic.

In the Subscriptions tab, choose to create a subscription. Note: The ARN for your topic should be pre-populated. If not, search for it by name.

Select "Email" for the protocol and add your email address as the Endpoint.

Check your email and confirm your subscription. Now, whenever an alarm is triggered, you will be notified!

<!-- Trigger some alarms -->
# Option 1: Add an error to the code!

In your Users Lambda function, mess something up, and deploy it! For example, change "lambda_handler" to "lambda_handlr" (missing 'e').

Run the unit test suite. Tests should fail. Now, try to access the API. (It should also fail!) Check the logs.

You should see the error in the logs. And, if you subscribed to the SNS topic, you should receive notification from SNS that your Lambda function failed.

*****Do not forget to fix the errors you introduced and re-deploy the function before proceeding further !

# Option 2: Force Lambda function throttling

Throttling is when your Lambda function is so busy that it cannot handle an additional request. You simulate this by setting the reserved concurrency for the function to zero (0):

    aws lambda put-function-concurrency \
        --function-name  <UsersFunction name from the stack outputs>  \
        --reserved-concurrent-executions 0
        
Again, try accessing the API (which should fail). And, if you subscribed to the SNS topic, you should receive notification from SNS that your Lambda function has been throttled.