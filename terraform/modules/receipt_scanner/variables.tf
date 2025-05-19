variable "lambda_image_uri" {
  description = "The URI of the Docker image in ECR to be used for the Lambda function"
  type        = string
  default     = "046873714594.dkr.ecr.eu-west-2.amazonaws.com/receipt_scanner:latest"
}

variable "uploader_image_uri" {
  type = string
  default = "046873714594.dkr.ecr.eu-west-2.amazonaws.com/receipt_uploader:latest"
}

variable "history_image_uri" {
  type = string
  default = "046873714594.dkr.ecr.eu-west-2.amazonaws.com/receipt_history:latest"
}
variable "region" {
  default = "eu-west-2"
  type = string
}

