# link to workshop: https://catalog.workshops.aws/serverless-patterns/en-US/dive-deeper/module2a

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
- For pipeline template, choose: 1 - AWS Quick Start Pipeline Templates
- For CI/CD system, choose: 5 - AWS CodePipeline
- For pipeline template choose: 1 - Two-stage pipeline
- Enter Y to go through the stage setup process
