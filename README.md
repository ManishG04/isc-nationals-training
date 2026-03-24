# isc-nationals-training


### ECS Task Definition Using CodePipeline
`buildspec.yaml`
```yaml
version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws --version
      - ACCOUNT_ID=$(echo $CODEBUILD_BUILD_ARN | cut -f5 -d ':') && echo "The Account ID is $ACCOUNT_ID"
      - echo "The AWS Region is $AWS_DEFAULT_REGION"
      - REPOSITORY_URI=$ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$ACCOUNT_ID-application
      - echo "The Repository URI is $REPOSITORY_URI"
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $REPOSITORY_URI
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=$COMMIT_HASH

  build:
    on-failure: ABORT
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $REPOSITORY_URI:$IMAGE_TAG .
      - docker tag $REPOSITORY_URI:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG

  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo Writing image definitions file...
      - printf '[{"name":”myimage","imageUri":"%s"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json
      - printf '{"ImageURI":"%s"}' $REPOSITORY_URI:$IMAGE_TAG > imageDetail.json
      
artifacts:
    files: 
      - imagedefinitions.json
      - imageDetail.json
      - appspec.yaml
      - taskdef.json
```


### Token, Region, Family and Account_ID
```bash
TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
AWS_REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region) 
FAMILY=$(aws ecs list-task-definition-families --status ACTIVE --output text | awk '{print $NF}') 
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) 
printf "You are using $AWS_REGION region\nYour task definition family is $FAMILY\nYour account ID is $ACCOUNT_ID\n"
```

```json
{
    "containerDefinitions": [
        {
            "name": "application",
            "image": "<IMAGE_NAME>",
            "portMappings": [
                {
                    "containerPort": 80,
                    "hostPort": 80,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "cicd-logs",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ],
    "family": "LabStack-cebead2c-16d0-4e62-b71e-9aa4dd3d2714-9m8zrsA37Mf37qrAvndYWs-0-TaskDefinition-tOSnjtDhVUw8",
    "taskRoleArn": "arn:aws:iam::811714540609:role/ecsTaskExecutionRole",
    "executionRoleArn": "arn:aws:iam::811714540609:role/ecsTaskExecutionRole",
    "networkMode": "awsvpc",
    "status": "ACTIVE",
    "compatibilities": [
        "EC2",
        "FARGATE"
    ],
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "cpu": "256",
    "memory": "512",
    "tags": [
        {
            "key": "Name",
            "value": "GreenTaskDefinition"
        }
    ]
}
```
