In traditional development, dozens of potential frameworks are available in as many languages. These frameworks help you process requests and return responses.

Components exist to parse URL parameters, retrieve headers and cookies, verify authentication, and route requests to a method to process and return a response. The method or function usually connects to a data source, queries and retrieves records, then returns some message directly to the client. Applications built with traditional frameworks do offer a lot of ready-built functionality. You could run your existing architectures in the cloud, but you would still need to manage servers.

# Event Driven Architecture
Serverless architecture brings development flexibility, scalability, and the capability to expand quickly into new geographical regions. The key to these benefits is a loosely coupled architecture.

Serverless solutions, even the basic one you built in this module, are based on event-driven architecture or EDA. In event-driven architectures, services send and receive events which represent changes in state or an update.

In this module, you built a synchronous pattern to respond to a request for users, but it still used an event-driven workflow. Events contain the data in a chunk of JSON text. Services expect specific shapes of JSON. This format represents data structures with consistent shape but flexible contents, that aren't row or column based.

API Gateway served as the entry point for the Users microservice. Similar to traditional web application URL-routers, API Gateway takes the inbound request to the /users endpoint and converts it into an event. That event was routed to a Lambda function.

The Lambda service manages the function. After initializing an execution environment, the Lambda service invokes the function to handle the inbound event, and possibly many more events during the function lifecycle.

The function connects to a serverless database table, retrieves data, and bundles that data into a JSON response event.

Instead of sending the response directly to the client, the response event is sent back to API Gateway. API Gateway then forwards the body of the event to the calling client to complete the request/response cycle.

In event-driven architecture, services do not know how events will be processed further. This creates flexibility to extend the system, independent of other components. This is a big difference from traditional frameworks, providing immense opportunity to add features to your solution without disrupting an existing, operating solution!

# Summary
Event-driven architecture is foundational for serverless.
Scalable and extendable solutions are built from loosely coupled components which communicate changes of state or updates through events, which consist of JSON data.

Continue your journey by building a Users Service with authentication, authorization, and automated deploy with Serverless Application Model (SAM). You will add unit-tests, observability, alarms, and a dashboard to monitor the application!

Before moving on, it's always a good idea to learn how to cleanup resources to prevent unexpected use...