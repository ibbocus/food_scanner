output "lambda_function_name" {
  value       = aws_lambda_function.processor.function_name
  description = "Deployed Lambda function name"
}

output "api_gateway_rest_api_id" {
  value       = data.aws_api_gateway_rest_api.api.id
  description = "API Gateway REST API ID"
}
