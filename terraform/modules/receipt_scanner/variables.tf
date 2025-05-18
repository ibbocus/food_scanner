variable "lambda_image_uri" {
  description = "The URI of the Docker image in ECR to be used for the Lambda function"
  type        = string
  default     = "046873714594.dkr.ecr.eu-west-2.amazonaws.com/receipt_scanner@sha256:bdc8b713c5ca3a2b1035689f4863a944db22492b8cf23b090049a66fac3c8132"
}

variable "region" {
  default = "eu-west-2"
  type = string
}

