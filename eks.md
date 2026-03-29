## EKS Troubleshooting: The "Fixer" Protocol

## 1. The Master Key (Authentication)
Before you can run a single kubectl command, you have to prove to the EKS Control Plane who you are. This bridges your AWS IAM identity with Kubernetes RBAC.

The Command:

```Bash
aws eks update-kubeconfig --region us-east-1 --name <cluster-name>
```
- What it actually does: It reaches out to AWS, grabs the cluster's certificate authority, and writes a temporary login token into a hidden file on your EC2 instance (~/.kube/config).

- The "Fixer" Gotcha: If you run this and still get an Unauthorized error when trying to run kubectl, it means the AWS IAM Role you are currently using was not added to the cluster's aws-auth ConfigMap by the administrator. (In a Jam, this usually means you forgot to run sudo su - ec2-user to assume the correct role).

## 2. The Radar (Reconnaissance)
You use this to get a bird's-eye view of the battlefield and spot exactly which container is bleeding.

The Command:

```Bash
kubectl get pods -n <namespace> -o wide
```
(Note: If you don't know the namespace, use -A to show every pod in the entire cluster).

The Flags:

- -n: Specifies the namespace (e.g., -n production or -n default).

- -o wide: This is the secret weapon. It adds extra columns to the output, showing you the exact Worker Node IP the pod is living on. (Crucial if only one specific EC2 node is broken).

The Status Cheat Sheet:

- Running: The infrastructure is healthy. (If the website is still down, the Python/Node code is broken. Go to Step 4).

- Pending: The pod cannot fit on the current EC2 instances. (You need more CPU/RAM, or the Auto Scaler is broken).

- ImagePullBackOff / ErrImagePull: Kubernetes cannot download your Docker image. (Typo in the ECR URI, or your EC2 node is missing the AmazonEC2ContainerRegistryReadOnly IAM policy).

- CrashLoopBackOff: The application booted up, hit a fatal error, and violently crashed.

## 3. The Autopsy (Infrastructure Diagnostics)
If a pod is stuck in Pending or ImagePullBackOff, do not check the application logs. The code hasn't even started running yet. You must ask Kubernetes what went wrong.

The Command:

```Bash
kubectl describe pod <broken-pod-name> -n <namespace>
```
How to read it: Do not read it top-to-bottom. Scroll instantly to the absolute bottom to the Events section. It reads like a chronological diary of what the Control Plane tried to do.

What to look for:

- "FailedScheduling: 0/3 nodes are available: 3 Insufficient memory."

- "Liveness probe failed: HTTP probe failed with statuscode: 500" (Your app is freezing up).

- "MountVolume.SetUp failed... secret not found" (You spelled the secret name wrong in your deployment YAML).

## 4. The Black Box (Application Diagnostics)
If the pod says Running or CrashLoopBackOff, the Kubernetes infrastructure did its job perfectly. The error is inside your Python/Node.js code.

The Command:

```Bash
kubectl logs <broken-pod-name> -n <namespace> --tail=50 -f
```
The Flags:

- --tail=50: Only prints the last 50 lines. (Prevents your terminal from freezing if the app has printed 10,000 lines of logs).

- -f: "Follow" mode. It streams the logs live on your screen like a matrix terminal.

The "Ghost" Gotcha: If a pod crashed a minute ago and just restarted, running this command will only show you the fresh, empty logs of the new container. To see the logs of the container that died, add the --previous flag:
kubectl logs <broken-pod-name> -n <namespace> --previous

## 5. The Sledgehammer (Force Restart)
Kubernetes is declarative. If you fix a database password in AWS Systems Manager or a ConfigMap, the running Pod does not magically know you changed it. You have to kill it so it reads the new password on boot.

The Command:

```Bash
kubectl delete pod <broken-pod-name> -n <namespace>
```
What it actually does: It assassinates the container. The EKS Control Plane immediately panics ("Wait, the Deployment says we need 3 pods, but we only have 2!") and instantly spins up a brand new, healthy replacement that pulls your updated configurations.

The "Fixer" Gotcha: Only do this if the Pod is managed by a Deployment or ReplicaSet (which is 99% of the time in a Jam). If it is a bare, standalone pod, deleting it erases it forever.


## Scenario 1: The "No Engine" Trap (Missing Node Group)
The Problem: The Kubernetes brain is running, but it has no body. There are zero EC2 instances attached to the cluster, so your applications have nowhere to run.
How to diagnose it: Open your terminal and type: kubectl get nodes
If it returns No resources found, you have found the missing piece.

### How to build it (The Fix):

1. Go to the EKS Console in AWS.

2. Click on your Cluster name.

3. Click the Compute tab.

4. Scroll down to Node Groups and click Add Node Group.

Name it (e.g., worker-nodes), select the IAM Role (they usually pre-create one called eks-node-role), and choose your EC2 instance types (usually t3.medium or t3.large).

Click Next and Create. Once they spin up, your cluster is fully built.

## Scenario 2: The "Serverless" Trap (Missing Fargate Profile)
The Problem: The cluster is running, and the instructions tell you the application must be "Serverless." But when you look at the pods, they are stuck in a Pending state forever.
How to diagnose it:
Type: kubectl describe pod <pod-name>
If the bottom events say something like: "FailedScheduling: no nodes available to schedule pods", the cluster doesn't know how to use Fargate.

### How to build it (The Fix):

1. Go to the EKS Console -> Click your Cluster -> Compute tab.

2. Scroll down to Fargate Profiles and click Add Fargate Profile.

3. Name it, select the eks-fargate-role.

4. The Critical Step: In the "Namespace" box, type the exact namespace your app is trying to deploy into (e.g., default or production).

5. Click Create. EKS will now automatically spin up serverless containers for your app.

## Scenario 3: The "Identity Crisis" (Missing OIDC / IRSA)
The Problem: The application boots up perfectly, but the Python/Node code keeps crashing because it says "Access Denied to S3" or "Cannot read DynamoDB."
### How to diagnose it:
Type: kubectl logs <pod-name> and look for AWS permission errors.
Why this happens: The EC2 node has an IAM role, but in modern EKS, AWS wants you to give the IAM role directly to the Kubernetes Pod. This requires a bridge called an OIDC Provider.

### How to build it (The Fix):

1. Go to the EKS Console -> Click your Cluster -> Overview tab.

2. Look at the bottom for OpenID Connect provider URL.

3. If it is blank or there is a button that says Associate Identity Provider, click it!

Once associated, you go to IAM -> Roles -> Create a Role -> Select Web Identity -> Choose your new EKS OIDC provider, and attach the S3/DynamoDB policies.

## The "Panic Button" Strategy
If you get to the EKS module and you are completely lost, do not randomly click things in the AWS Console. Fall back to your diagnostic reflexes.

The exact second the module starts, run these two commands:

kubectl get nodes (Checks if you need to build Scenario 1).

kubectl get pods -A (Checks if things are stuck in Pending or crashing).

You don't need to be a Kubernetes expert to survive this module; you just need to know how to connect AWS infrastructure (EC2/Fargate/IAM) to the EKS cluster shell they gave you.

Based on those three scenarios, does the Node Group (EC2) or the Fargate Profile (Serverless) sound more like the kind of architecture your Chief Expert usually tests you on?


## The 3 "Difficulty Multipliers" (How they trick you)
### 1. The "Red Herring" Logs Trap

The Setup: The website returns a 500 Internal Server Error.

The Trap: You run kubectl logs and see a massive Python error saying ConnectTimeout: database.internal. You spend 45 minutes rewriting the Python database connection string.

The Reality: The Python code was perfect. The EC2 Worker Node just didn't have the AWS Security Group permission to talk to the RDS database.

The Fixer Rule: Always check AWS Networking (Security Groups/VPCs) before you blame the Kubernetes Pod.

### 2. The YAML Indentation Assassin

The Setup: They ask you to deploy a simple Nginx web server. They give you a deployment.yaml file to apply.

The Trap: You run kubectl apply -f deployment.yaml and it throws a massive syntax error.

The Reality: Kubernetes YAML is violently strict. If you are missing one single space, or if you use a "Tab" instead of two "Spaces," the entire deployment crashes.

The Fixer Rule: If you have to edit YAML in VS Code, make sure the bottom right corner of VS Code says "Spaces: 2", not "Tab Size: 4".

### 3. The IAM vs. RBAC Collision

The Setup: You fixed the OIDC provider (Scenario 3 from earlier), but the Pod still says "Access Denied."

The Trap: You stare at the AWS IAM Role for 30 minutes, confirming it has S3FullAccess.

The Reality: In Kubernetes, there is AWS IAM (which talks to AWS services), and there is RBAC (Role-Based Access Control, which dictates who can do what inside the cluster). You might have fixed the AWS side, but the Kubernetes ServiceAccount wasn't linked to it.