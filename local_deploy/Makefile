# Makefile to manage LocalStack services: Lambda and S3

.PHONY: init build_lambda deploy_lambda start stop clean

init:
	@echo "Starting LocalStack..."
	docker-compose -f docker-compose-local.yaml up -d

build_lambda:
	@echo "Packaging Lambda function as ZIP..."
	cd ../lambda/fetch_articles && zip -r9 function.zip .

deploy_lambda:
	@echo "Deploying ZIP-based Lambda function to LocalStack..."
	awslocal lambda create-function \
		--function-name fetchArticles \
		--runtime python3.9 \
		--handler lambda_function.lambda_handler \
		--zip-file fileb://../lambda/fetch_articles/function.zip \
		--role arn:aws:iam::000000000000:role/lambda-role \
		--region us-east-1

start: init build_lambda deploy_lambda

stop:
	@echo "Stopping LocalStack..."
	docker-compose -f docker-compose-local.yaml down

clean:
	@echo "Removing LocalStack volumes..."
	docker-compose -f docker-compose-local.yaml down -v
rebuild:
	@echo "Rebuilding all services..."
	docker-compose -f docker-compose-local.yaml up --build -d