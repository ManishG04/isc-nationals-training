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