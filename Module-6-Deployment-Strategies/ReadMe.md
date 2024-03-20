# Link to workshop: https://catalog.workshops.aws/serverless-patterns/en-US/dive-deeper/module2b

# NO NEED TO DO WORKSHOP BECAUSE IT IS SAME WITH MODULE-5 OF MY SAM WORKSHOP: https://github.com/lacareer/SAM (https://github.com/lacareer/SAM/tree/master/mod-5-canary)

<!-- Deployment Strategies -->

# Solution architecture
In this module, you will update your pipeline to use a blue/green deployment and then a canary deployment. A Lambda alias is used to direct traffic to a specific version of a function. In this scenario, an alias named live will point to the deployed version and during the blue/green deployment, the pipeline will update the live alias to point to the new Lambda function version.

With these deployment strategies, you can test your deployment using a small sample of traffic and instantly rollback your application to the previous version(the blue environment) in the event of an issue.

# Blue/Green deployment
In a blue/green deployment, two separate, yet identical, environments will exist during the deployment. The blue environment runs the current application version and the green environment runs the updated application version. During deployment, 100% of the traffic is shifted to the new (green) environment, but the original (blue) environment is still available.

In the Blue/Green Deployment step, 100% of the traffic is shifted to the green environment (New Production) during deployment.


# Canary deployment
A canary deployment is just like a blue/green deployment, the only difference is the traffic shifting pattern between the blue and green environments. During deployment, traffic is gradually shifted to the new environment by defining a percentage of traffic to shift within a given time period. This small, initial shift is your canary that allows you to test your deployment with a small traffic sample, and validate your new environment works as expected.

In the Canary Deployment step, 10% of the API traffic is shifted to the new version during the first 5 minutes. The remaining 90% of traffic is shifted after the first 5 minutes.

The following diagram is the deployment progression. Canary (10%) represents the 10% shift to the green environment. New Production represents the completed deployment where 100% of traffic is directed to the green environment.

<!-- What you will accomplish -->

- Modify template.yaml to create the first version of CodeDeploy

- Modify the UsersFunction Lambda by blue/green deployment

- Modify the UsersFunction Lambda by canary deployment

- Test auto rollback when associated CloudWatch alarm is raised during canary deployment
