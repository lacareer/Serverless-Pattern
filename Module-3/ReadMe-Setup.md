
<!-- Continue from Module-2 -->
If you completed module 2 - Synchronous Invocation and kept the resources, skip ahead to Create a project (I was my case).

<!-- Deploy prerequisite resources (if necessary) -->
If you did not complete module 2 - Synchronous Invocation, or you want to start from a known-good start state, take these steps.


<!-- To set up a fresh start state -->

In the IDE terminal, run the following commands:
    # Download the base stack file tree and SAM configuration

    cd ~/environment

    wget -O ws-serverless-patterns.zip "https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/76bc5278-3f38-46e8-b306-f0bfda551f5a/module3/sam-python/ws-serverless-patterns-2023-09-18.zip"

    unzip ws-serverless-patterns.zip

    cd ws-serverless-patterns

<!-- Create a project for this module -->
Confirm that prerequisites resources are deployed before taking this step if you did not complete Module-2

1. In the Cloud9 terminal, change to the workshop directory:

    cd ~/environment/ws-serverless-patterns

2. Download and run the setup script for this module:

    wget -O module3_setup.sh 'https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/76bc5278-3f38-46e8-b306-f0bfda551f5a/module3/sam-python/module3_setup-2023-09-18.sh'
    
    chmod +x module3_setup.sh
    
    source ./module3_setup.sh
