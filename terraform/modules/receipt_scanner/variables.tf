variable "lambda_image_uri" {
  description = "The URI of the Docker image in ECR to be used for the Lambda function"
  type        = string
  default     = "046873714594.dkr.ecr.eu-west-2.amazonaws.com/receipt-scanner-046873714594:latest"
}

variable "region" {
  default = "eu-west-2"
  type = string
}

