# 🚨 API Gateway: The 5XX Autopsy
Since you are already planning for the future and dissecting yesterday's architecture, let’s look at the 5XX errors.

A 4XX error means the client messed up (bad password, wrong URL). A 5XX error means the server messed up. When API Gateway throws a 5XX, it is almost always an integration failure between the Gateway and your backend (Lambda/ALB).

Here are the specific scenarios that trigger them:

## 💥 500 Internal Server Error (The Mapping Crash)
API Gateway itself threw up its hands and crashed.

The Scenario: You are using VTL (Velocity Template Language) to transform data before sending it to the backend. You wrote a bug in your VTL script (like trying to parse a missing JSON variable). API Gateway crashes trying to read it.

The Fix: Check the API Gateway execution logs in CloudWatch. It will tell you exactly which line of the mapping template failed.

## 🧟 502 Bad Gateway (The "Malformed Proxy" Trap)
This is the absolute most common error when using Lambda Proxy Integration.

The Scenario: API Gateway successfully forwarded the request to your Lambda function. The Lambda function ran perfectly and returned "User created successfully". API Gateway then throws a 502.

Why it happens: In a Proxy Integration, API Gateway expects the Lambda to do the HTTP formatting. If your Lambda doesn't return a strict JSON object containing exactly "statusCode", "headers", and "body", API Gateway doesn't know how to translate it back to the user, assumes the backend is broken, and throws a 502.

## 🧱 503 Service Unavailable (The Missing Bridge)
API Gateway tried to reach the backend, but the connection was physically impossible or refused.

The Scenario: You are routing to an ALB in a private subnet.

Why it happens: 1. Your VPC Link is broken or pointing to the wrong subnets.
2. The ALB's Security Group is blocking the traffic from the VPC Link.
3. You are routing to a Lambda function, but the Lambda function’s concurrency limit is set to 0 (it is turned off).

## ⏳ 504 Gateway Timeout (The 29-Second Hard Limit)
This is a classic AWS Jam trap.

The Scenario: You have an API Gateway triggering a Lambda function that processes a massive video file. The Lambda function works perfectly and finishes the job in 45 seconds. The user gets a 504 error.

Why it happens: API Gateway has an un-changeable, hard-coded timeout limit of 29 seconds. If your backend takes 30 seconds to reply, API Gateway cuts the cord and returns a 504, even if the backend is still happily working.

The Fix: You must decouple the architecture. API Gateway should put the request into an SQS queue (which returns a fast 200 OK to the user), and then a backend worker processes the queue asynchronously.