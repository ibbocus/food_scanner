provider "aws" {
  region = var.region
}

module "infra" {
  source          = "./image-upload-api"
  region          = var.region
  account_id      = var.account_id
  lambda_zip_path = "lambda.zip"
}

module "frontend_s3" {
  source      = "./s3-website-hosting"
  bucket_name = "food-scanner-046873714594"

}

