 <!-- Test Function locally -->
 Before connecting the function to URLs with different incoming HTTP methods, you might want to test the function locally in isolation.

<!-- Set up test environment & event -->
For local tests, you need to set up environment variables and events used by your function(s).

1.Set environment variables

In ~/path_to_serverless/ws-serverless-patterns/users, create a new file named env.json. This file will contain the environment variables needed by your Lambda functions.

2. Paste the following JSON into env.json, substituting in the UsersTable value from the previous deploy output:
    {
    "UsersFunction": {
        "USERS_TABLE": "<UsersTable output value from previous deploy>"
    }
}

3.Set up a test event

An event is always needed to invoke a Lambda function. In Module 1, you created a test event in the Lambda Console.

In this module, you will use event files stored in the /events directory.

Open ~/path_to_serverless/ws-serverless-patterns/orders/events/event-post-user.json in the editor. It should look like the following JSON snippet and will test one resource path. Events can be created to test each resource and path in the application. The additional files in this folder will be used later for unit testing.

    {
        "resource": "/users",
        "path": "/users",
        "httpMethod": "POST",
        "headers": null,
        "multiValueHeaders": null,
        "queryStringParameters": null,
        "multiValueQueryStringParameters": null,
        "pathParameters": null,
        "stageVariables": null,
        "requestContext": {
            "requestId": "be946131-30c4-4396-9c29-f25f8caa91dc"
        },
        "body": "{\"name\":\"John Doe\"}",
        "isBase64Encoded": false
    }

<!-- Invoke the function -->
Now that the environment and event are ready, invoke the function locally to verify it:

    sam local invoke -e events/event-post-user.json -n env.json

The first time this runs, SAM will build a container image (make sure docker service is r unning or the docker desktop for windows is running and integrated with wsl if that is what you are using).  
This will take a minute or so. Subsequent runs will be immediate.

You should eventually see a response, similar to the following, with a 200 status and data for a new User record:

    {"statusCode": 200, 
    "body": "{\"name\": \"John Doe\", 
    \"timestamp\": \"2022-06-21T20:25:16.342221\", 
    \"userid\": \"430a7594-f1a0-11ec-a87a-0242ac110002\"}", 
    "headers": {
        "Content-Type": "application/json", 
        "Access-Control-Allow-Origin": "*"}}

The response is in the shape of a Lambda function with proxy integration . The response includes the HTTP response status code, response headers, and the payload that was sent by the Lambda function to the DynamoDB as a new record data.

<!-- Verify new record was created -->
Option 1: Use the DynamoDB Console

Remember: look for the table and 'explore items'.

Option 2: Use the AWS CLI

This method tries to retrieve the new item from DynamoDB:
# Check that table-name is the UsersTable value (case sensitive) from the CloudFormation output.
# Also, make sure you replace <userid-from-response> with the userid value returned in the invoke result JSON.
    aws dynamodb get-item --table-name ws-serverless-patterns-users-Users --key '{"userid": {"S": "<userid-from-response>"}}' 

<!-- Invoke function to create user with AWS CLI -->
Find the function name from the stack or console. You will need the Physical ID not the logical name.
Change the name in events/event-post-user.json then invoke this command:

    aws lambda invoke --function-name ws-serverless-patterns-users-UsersFunction-xxxxxxxxxx \
    --cli-binary-format raw-in-base64-out  \
    --payload file://events/event-post-user.json \
    response.json

Then run to see result:

    cat response.json


