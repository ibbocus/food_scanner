data "aws_api_gateway_rest_api" "api" {
  name = "seminal"
}

resource "aws_api_gateway_resource" "request" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  parent_id   = data.aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "request"
}

resource "aws_api_gateway_method" "get_request" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.request.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_method" "options_request" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.request.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_request" {
  rest_api_id             = data.aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.request.id
  http_method             = aws_api_gateway_method.options_request.http_method
  type                    = "MOCK"
  passthrough_behavior    = "WHEN_NO_MATCH"
  request_templates = {
    "application/json" = <<EOF
{
  "statusCode": 200
}
EOF
  }
}

resource "aws_api_gateway_method_response" "options_response_200" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.request.id
  http_method = aws_api_gateway_method.options_request.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_method_response" "get_response_200" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.request.id
  http_method = aws_api_gateway_method.get_request.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

resource "aws_api_gateway_integration_response" "options_integration_response" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.request.id
  http_method = aws_api_gateway_method.options_request.http_method
  status_code = aws_api_gateway_method_response.options_response_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_integration_response" "get_integration_response" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.request.id
  http_method = aws_api_gateway_method.get_request.http_method
  status_code = aws_api_gateway_method_response.get_response_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
  }
}

resource "aws_api_gateway_integration" "get_lambda_proxy" {
  rest_api_id             = data.aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.request.id
  http_method             = aws_api_gateway_method.get_request.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.processor.invoke_arn
}

resource "aws_lambda_function" "processor" {
  function_name = "fetch_article"
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  role          = aws_iam_role.lambda_exec.arn
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_iam_role" "lambda_exec" {
  name = "fetch_articles_lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  depends_on = [
    aws_api_gateway_integration.get_lambda_proxy
  ]
}

resource "aws_api_gateway_stage" "dev" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  stage_name    = "dev"
}
