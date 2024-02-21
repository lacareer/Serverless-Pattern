# link to workshop: https://catalog.workshops.aws/serverless-patterns/en-US/dive-deeper/module2a

# NOTE THAT THE EMPHASIS OF THIS MODULE IS TO SHOW HOW TO CREATE A CICD PIPELINE FOR SERVERLESS APPLICATIONS AND USE CODEBUILD FOR TESTION
# SO, GO THROUGH THE BUILDSPECS IN PIPELINE/* AND HOW THEY INSTALL PACKAGES AND RUN THE UNIT/INTEGRATION TESTS

In this module, you will set up continuous integration and deployment (CI/CD). After your CI/CD pipeline is set up, commits to your code repository will kick off a series of steps to build, package, test, and promote your infrastructure and code to production.

If steps in the process, such as IntegrationTest, fail, the pipeline will be blocked. This is beneficial because that failure will prevent broken code or incorrectly configured infrastructure from being promoted into your production environment.

<!-- What you will accomplish -->
Create and add your code to a source repository
Configure and deploy a pipeline with two stages: dev and prod
Add automatic unit and integration testing into the pipeline

<!-- Setup  -->

# Project directory
- create a project directory ws-serverless-patterns/users

- cd into ws-serverless-patterns/users

## To create and initialize your code repository -->
Run the following command to create your CodeCommit repository ws-serverless-patterns-users:

    aws codecommit create-repository --repository-name ws-serverless-patterns-users --repository-description "Serverless Patterns"

Navigate to the ~/ws-serverless-patterns/users directory and initialize the Git repository:

    cd ~/environment/ws-serverless-patterns/users
    git init -b main

Add a Git remote for the repository you just created:

    git remote add origin codecommit::<AWS Region you created repository in>://ws-serverless-patterns-users

Finally, push your new project to the CodeCommit repository:

    Add a ReadMe.md with some dummy content so you can carry out the below command without it erroring out

    git add .
    git commit -m "Initial commit"
    git push --set-upstream origin main

You can review the new repository in AWS Management Console for Code Commit . If you do not see it, make sure the correct region is selected.

<!-- 1 - Create Pipeline -->

- create a project directory ws-serverless-patterns/users

- cd into ws-serverless-patterns/users

- In the user directory, run the following command and respond to the prompts:

    sam pipeline init --bootstrap

# Choose the following options at the prompts:

- For pipeline template, choose: "1 - AWS Quick Start Pipeline Templates"

- For CI/CD system, choose: "5 - AWS CodePipeline"

- For pipeline template choose: "1 - Two-stage pipeline"

- Enter Y to go through the stage setup process

# Set up Stage 1

- For Stage definition, enter "dev"

- For Account details, choose credential source "2 - default (named profile)"

- For Reference application build resources, accept all default values

- After reviewing the Summary, press enter to confirm, then choose Y at prompt to proceed with creation

- Wait for dev stage resources to be created. This can take several minutes...

# Set up Stage 2
At this point, one stage will be detected. When prompted to go through another stage setup process, accept the default Y to continue.

- For Stage definition, enter "prod"

- For Account details, choose credential source "2 - default (named profile)"

- For Reference application build resources, accept all default values

- After reviewing the Summary, press enter to confirm, then choose Y at prompt to proceed with creation

- Again, wait for prod stage resources to be created...

# Connect a git provider
After the resources are created, the bootstrap process

- For Git provider, choose "2 - CodeCommit"

- For repository name, enter "ws-serverless-patterns-users"

- For Git branch, enter "main"

- For template file, accept the default template.yaml

# Finish the configuration
The process should detect two stage configuration names, 1 - dev and 2 - prod. The last thing you need to do is configure the stack names to be used for these two stages.

- When prompted to select an index, enter 1

- For application stack name for stage 1, enter ws-serverless-patterns-users-dev

- When prompted to select an index again, enter 2

- For application stack name for stage 2, enter ws-serverless-patterns-users-prod

- Wait for the generation process to complete...

<!-- Deploy the pipeline -->
Add the files to git, then push the new pipeline specific configuration files to the CodeCommit repository:

    git add .
    git commit -m "Add CI/CD pipeline configuration"
    git push

Finally, deploy the pipeline to CloudFormation by running the following AWS CLI command:

    aws cloudformation create-stack --stack-name ws-patterns-pipeline --template-body file://codepipeline.yaml --capabilities CAPABILITY_IAM

Wait for the CloudFormation to finish the deployment...

Alternatively, you can run the following AWS CLI command to check status:

    aws cloudformation describe-stacks --stack-name ws-patterns-pipeline

<!-- Verify the pipeline -->
You can check out the CI/CD pipeline in the AWS CodePipeline Management Console . This console will show all the steps, current status, and any errors (if they exist).

# Congratulations! Changes in your repository will automatically update your infrastructure stack!

<!-- 2 - Automate Testing -->
After you have a CI/CD pipeline in place, you can automate the unit and integration test steps.

# Activate tests for the pipeline
The SAM pipeline configuration in codepipeline.yaml includes unit and integration tests, but the blocks are commented out and therefore inactive. 

You must uncomment each of these sections to activate testing in the pipeline.

Open codepipeline.yaml and make the following changes:

# Activate Unit Tests

- Find the text: Uncomment and modify the following step for running the unit-tests
    Uncomment the following section. Repeat in all locations.

- Find the text: Uncomment the line below to enable the unit-tests
    Uncomment the following line.

# Activate Integration Tests

- Find the text: Uncomment the following step for running the integration tests
    Uncomment the following section. Repeat in all locations.

- Find the text: Uncomment and modify the following step for running the integration tests
    Uncomment the following section. Repeat in all locations.

<!-- Set up environment variables -->
You need to copy the EnvironmentVariables section from the DeployTest action to the IntegrationTest action.

- Find the Pipeline resource stage named DeployTest

- Select and copy the entire EnvironmentVariables property section (10 lines)

- Paste this EnvironmentVariables section into the IntegrationTest > Configuration section, under ProjectName

When complete, the IntegrationTest action should look like the following:

##
# Uncomment the following step for running the integration tests
    - Name: IntegrationTest
    ActionTypeId:
        Category: Build
        Owner: AWS
        Provider: CodeBuild
        Version: "1"
    Configuration:
        ProjectName: !Ref CodeBuildProjectIntegrationTest
        EnvironmentVariables: !Sub |
        [
            {"name": "ENV_TEMPLATE", "value": "packaged-test.yaml"},
            {"name": "ENV_REGION", "value": "${TestingRegion}"},
            {"name": "ENV_STACK_NAME", "value": "${TestingStackName}"},
            {"name": "ENV_PIPELINE_EXECUTION_ROLE", "value": "${TestingPipelineExecutionRole}"},
            {"name": "ENV_CLOUDFORMATION_EXECUTION_ROLE", "value": "${TestingCloudFormationExecutionRole}"},
            {"name": "ENV_BUCKET", "value": "${TestingArtifactBucket}"},
            {"name": "ENV_IMAGE_REPOSITORY", "value": "${TestingImageRepository}"}
        ]
    InputArtifacts:
        - Name: SourceCodeAsZip
    RunOrder: 2
##

<!-- Update permissions to allow testing -->
Integration tests require allow permissions so that they may run.

- Find the resource name: CodeBuildServiceRole:
- Scroll down to the Policies: section.
- Add the following four (4) policies into this section:

# Policy 1: Add permission to describe CloudFormation stack being tested
- PolicyName: CloudFormationStackAccess
    PolicyDocument:
    Version: "2012-10-17"
    Statement:
        - Effect: Allow
        Action:
            - "cloudformation:DescribeStacks"
        Resource:
            - !Sub "arn:aws:cloudformation:${AWS::Region}:${AWS::AccountId}:stack/${TestingStackName}/*"
# Policy 2: Add permission to generate random password using SecretsManager
- PolicyName: GeneratePassword
    PolicyDocument:
    Version: "2012-10-17"
    Statement:
        - Effect: Allow
        Action:
            - "secretsmanager:GetRandomPassword"
        Resource:
            - "*"
# Policy 3: Add permission to access/modify DynamoDB data being tested (used by test configuration/initialization)
- PolicyName: DynamoDBAccess
    PolicyDocument:
    Version: "2012-10-17"
    Statement:
        - Effect: Allow
        Action:
            - "dynamodb:BatchGet*"
            - "dynamodb:DescribeStream"
            - "dynamodb:DescribeTable"
            - "dynamodb:Get*"
            - "dynamodb:Query"
            - "dynamodb:Scan"
            - "dynamodb:BatchWrite*"
            - "dynamodb:CreateTable"
            - "dynamodb:Delete*"
            - "dynamodb:Update*"
            - "dynamodb:PutItem"
        Resource:
            -  !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${TestingStackName}-Users"
# Policy4: Add permission to manipulate Cognito users
- PolicyName: CognitoAccess
    PolicyDocument:
    Version: "2012-10-17"
    Statement:
        - Effect: Allow
        Action:
            - "cognito-idp:AdminDeleteUser"
            - "cognito-idp:AdminConfirmSignUp"
            - "cognito-idp:AdminAddUserToGroup"
        Resource:                  
            - !Sub "arn:aws:cognito-idp:${AWS::Region}:${AWS::AccountId}:userpool/*"

<!-- Modify pipeline build specifications -->
Next, you will specify the commands to run the tests.

To set up unit tests
Open pipeline/buildspec_unit_test.yml file in an editor.
Update the template to use the same commands from the Unit Test step:

    version: 0.2
    phases:
    install:
        runtime-versions:
        python: 3.9
    build:
        commands:
        # trigger the unit tests here
        - echo 'Running unit tests'
        # Install all dependencies (including dependencies for running tests)
        - pip install -r requirements.txt
        - pip install -r ./tests/requirements.txt       
        # Discover and run unit tests in the 'tests/unit' directory
        - python -m pytest tests/unit -v

# Save and close the file

<!-- To set up integration tests -->
Open pipeline/buildspec_integration_test.yml
Update the template to use the same commands from the Integration Test step:
    version: 0.2
    phases:
    install:
        runtime-versions:
        python: 3.9
    build:
        commands:
        # trigger the integration tests here
        - echo 'Running integration tests'
        # Install all dependencies (including dependencies for running tests)
        - pip install -r requirements.txt 
        - pip install -r ./tests/requirements.txt 
        # Discover and run unit tests in the 'tests/unit' directory
        - python -m pytest tests/integration -v      

# Save and close the file

<!-- Lastly, push your updates to your repository: -->

    git add .
    git commit -m "Add unit & integration tests to CI/CD pipeline"
    git push

<!-- Verify test run -->
# Note that the test will fail when the unit and integration test are ran bcs there's not code to unit 
# Note that the deploy will fail if the deploy stage runs bcs there's serverless resources/template.yaml to deploy


After the template changes are committed and pushed to the CodeCommit repository, you can verify that the pipeline is running with tests.

Go to Code Pipelines Management Console 

Choose your region

Select your pipeline

Verify the pipeline contains a UnitTest step

<!-- Clean up -->
You can continue to use this CI/CD setup for other modules, or you can choose to delete the pipeline and related test stacks to keep your environment clean.

# To delete the CI/CD infrastructure stacks with SAM
The sam delete command is an efficient way to delete an entire stack and all associated resources. Your stack names could vary if you picked different names when creating your pipelines.

Run the following commands:

    sam delete --stack-name ws-serverless-patterns-users-dev
    sam delete --stack-name ws-serverless-patterns-users-prod
    sam delete --stack-name ws-patterns-pipelin

🙆 If you encounter a Validation Error similar to the following: "(ValidationError) when calling the DeleteStack operation: Role ws-patterns-pipeline-PipelineStackCloudFormationEx-XXXXXXXXXXXX is invalid or cannot be assumed", take these steps:

# This suggestion did not work for me
Open AWS Management Console
Navigate to IAM (Identity and Access Management)
Create a new role using the role name from your error message and:
If you are using Cloud 9 environment provided via Workshop Studio -
look up WSParticipantRole in the IAM and note AWS account trusted by the role,
click "Create role" button and select "AWS Account" option while creating the new role,
use account ID trusted by the WSParticipantRole.
Otherwise -
click "Create role" button
select CloudFormation service for the role.
Associate the policy AdministratorAccess with the new role
Try the sam delete command again
After the deletion completes, you must manually delete that role.

# However, the below worked for me (https://repost.aws/knowledge-center/cloudformation-role-arn-error)
it's a role problem, even if the user has the right policies you might do the following:

Open the IAM console.
In the navigation pane, choose Roles.
In the Role name column, choose the IAM role that's mentioned in the error message that you received.
If the roles doesn't exist:

Create a new IAM role (CloudFormationFullAccess)

Confirm that the new IAM role has the required permissions for AWS CloudFormation to perform create, update, or delete operations on resources in your stack.

then try

aws cloudformation delete-stack --stack-name YourStackName --role-arn arn:aws:iam::XXXXX:role/CloudFormationFullAccess (or the role name assigned)

  
