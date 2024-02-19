All resources were created using the AWS console

# Workshop link: https://catalog.workshops.aws/serverless-patterns/en-US

<!-- To create a DynamoDB table -->
    Login to the Amazon Web Services Console
    From Services, find and navigate to the DynamoDB console 
    From the DynamoDB page, choose Create table.
    For Table name, enter serverless_workshop_intro.
    For Partition key name, enter _id.
    For Partition key type, choose String.
    Accept default settings, then choose Create table.
<!-- To add items in the console -->
    From the navigation pane, choose Explore items.
    Select the serverless_workshop_intro table.
    Choose Create item.
    If not already selected, choose the Form view for easier data entry.
    For _id, enter 1.
    Choose Add new attribute, select String.
    For Attribute Name, enter Name, and for value, enter your name.
    Choose Create item.
    You should see yourself in the item list!
<!-- Create a Lambda function named addDataToDynamoDB -->
    Start by creating a simple serverless Lambda function. Spoiler alert: this function will not add data to the table, but it will help you understand the essentials to create, invoke, and update a Lambda function.

    Open the Lambda console .
    From the navigation pane, choose Functions.
    Choose Create function.
    Select Author from Scratch
    For Function name enter addDataToDynamoDB
    For Runtime, select Python 3.9
    Choose Create function.
    Edit lambda role to have DynamoDBFullAccess

# lambda code
#
import boto3
import uuid

def lambda_handler(event, context):
    table_name = 'serverless_workshop_intro'
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    result = None
    people = [
            { 'userid' : 'marivera', 'name' : 'Martha Rivera'},
            { 'userid' : 'nikkwolf', 'name' : 'Nikki Wolf'},
            { 'userid' : 'pasantos', 'name' : 'Paulo Santos'},
        ]

    with table.batch_writer() as batch_writer:
        for person in people:
            item = {
                '_id'     : uuid.uuid4().hex,
                'Userid'  : person['userid'],
                'FullName': person['name']
            }
            print("> batch writing: {}".format(person['userid']) )
            batch_writer.put_item(Item=item)
            
        result = f"Success. Added {len(people)} people to {table_name}."

    return {'message': result}
#
#

<!-- To Create the Lambda function named readDataToDynamoDB -->
    Create a new Lambda function from scratch running with Python 3.9 called: get-users
    Paste in the following code:
<!-- Connect a URL with API Gateway -->
Next, you will create the entry point for your Users microservice by connecting web requests to your Lambda function.

<!--  Lambda function for API Gateway named: readDataToDynamoDB -->
# code
#
    import boto3

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('serverless_workshop_intro')

    def lambda_handler(event, context):
    data = table.scan()
    return data['Items']
# 
#

1 - Create an API
API Gateway provides three main types of API: HTTP, REST, and WebSockets. The REST API workflow has more steps to set up than an HTTP API. Later modules will use the advanced testing and mocking features in the REST API.

For this module, you will create a REST API for the sample User data.

In the console, go to the API Gateway service
Make sure you have chosen the new console experience.
Choose the REST API API type, then Build.
For API name, enter ServerlessREST; keep the default endpoint type of Regional.
Choose Create API to continue.
Look closely: If the form asks for VPC endpoint IDs, cancel, go back, and choose REST API without "Private".

2 - Create a Resource in the REST API
You now have an API with an empty root element. You need to define a Users resource and path.

Choose Create Resource.
For the Resource name, enter users.
Choose Create Resource.

3 - Create a Method for the REST Resource
Lastly, you will create a method under the Users resource that corresponds to an HTTP method. You will bind that method to the get-users Lambda function.

Select /users, then choose the Create method button.
For Method type, Select GET
For Integration type, choose Lambda Function.
Select the region where your readDataToDynamoDB Lambda function was created (it should be selected by default)
To find the Lambda Function, start entering the function name: get-users then choose it it.
Choose Create method

# Pre-deploy API test
Before you deploy your new API, test it with the built-in API Gateway REST Test feature. This ensures the API responds as expected with fewer ways it can fail.

1.Choose Resources from the left panel.
2.Choose the GET method under the /users resource
3.Choose the Test tab.
4.Leave Query Strings and Headers empty; choose Test.
You should see the API response of 200, and a Response body with Items from the DynamoDB table.

Yay! You know the REST API endpoint works!

# Deploy the API
Before you can connect to your API from an external URL, you must deploy it.

And, before you can deploy the API, you need to create a stage. A stage can be used to denote environments like dev/qa/prod, versioned URLs like v1/v2, or really any string you'd like.

We recommend v1 for the stage, because we typically suggest setting up separate dev/qa/production accounts with their own infrastructure stacks. (You'll see how to automate this in the next module!)

Choose the Deploy API button.
For Deployment stage, choose New stage.
For stage name, enter v1.
For deployment description, enter Initial rollout of the API!.
Choose Deploy
The API Invoke URL will be in this format:

https://<UNIQUE-ID>.execute-api.<REGION>.amazonaws.com/<STAGE>/<RESOURCE>

# Test the deployed API
Now that the API is deployed, you can try it out!

1. Copy the Invoke URL to a browser window and try it...
    Oops! You got an error, right???
    You should have gotten an error message: "{"message":"Missing Authentication Token"}"

    That is because you are asking for the root resource at '/' which does not have an associated methods.

2. Append users to the URL to invoke the /users resource and try again!
It worked, right?!?