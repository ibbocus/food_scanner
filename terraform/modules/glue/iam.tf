# modules/glue/iam.tf
locals {
  source_bucket = split("/", replace(var.source_s3_path, "s3://", ""))[0]
  target_bucket = split("/", replace(var.target_s3_path, "s3://", ""))[0]
}

resource "aws_iam_role" "glue_service_role" {
  name = "openfoodfacts-glue-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "glue_s3_access" {
  name        = "openfoodfacts-glue-s3-access"
  description = "Allow Glue to read source & write target S3"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = ["arn:aws:s3:::${local.source_bucket}"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["arn:aws:s3:::${local.source_bucket}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject"]
        Resource = ["arn:aws:s3:::${local.target_bucket}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role_managed" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_s3_policy_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}
