#!/bin/bash

set -e

# Config
REPO_NAME=fetch-articles-lambda
IMAGE_TAG=latest
REGION=eu-west-2
LAMBDA_NAME=fetch_articles
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"
SERVICE_NAME=fetch_articles

# 1. Create ECR repository (ignore error if it exists)
aws ecr describe-repositories --repository-names "$REPO_NAME" --region $REGION >/dev/null 2>&1 || \
aws ecr create-repository --repository-name "$REPO_NAME" --region $REGION

# 2. Authenticate Docker with ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# 3. Build the Docker image
docker build -t "$REPO_NAME:$IMAGE_TAG" ../lambda/$SERVICE_NAME

# 4. Tag and push to ECR
docker tag "$REPO_NAME:$IMAGE_TAG" "$IMAGE_URI"
docker push "$IMAGE_URI"

# 5. Create the Lambda function
aws lambda create-function \
  --function-name "$LAMBDA_NAME" \
  --package-type Image \
  --code ImageUri="$IMAGE_URI" \
  --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
  --region $REGION