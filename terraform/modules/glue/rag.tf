locals {
  bucket_name        = "food-scanner-046873714594"
  collection_name    = "products-embeddings"
  glue_role_name     = "glue-food-products-role"
}

# existing bucket
data "aws_s3_bucket" "food_bucket" {
  bucket = local.bucket_name
}

# ---------- IAM ----------
resource "aws_iam_role" "glue_role" {
  name = local.glue_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name        = "${local.collection_name}-policy"
  type        = "encryption"
  description = "Encryption policy for ${local.collection_name}"
  policy = jsonencode({
    Rules = [
      {
        Resource     = ["collection/${local.collection_name}"]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

resource "aws_iam_role_policy" "glue_inline" {
  name = "glue-inline-policy"
  role = aws_iam_role.glue_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [data.aws_s3_bucket.food_bucket.arn, "${data.aws_s3_bucket.food_bucket.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = [
          "aoss:*",
          "opensearch:ESHttp*"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}


resource "aws_opensearchserverless_collection" "products" {
  name        = local.collection_name
  type        = "VECTORSEARCH"
  description = "Vector search collection for product embeddings"
  depends_on  = [aws_opensearchserverless_security_policy.encryption_policy]
}

resource "aws_opensearchserverless_access_policy" "glue_access" {
  name        = "glue-data-access"
  type        = "data"
  description = "Glue read/write"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${aws_opensearchserverless_collection.products.name}"]
          Permission   = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${aws_opensearchserverless_collection.products.name}/*"]
          Permission   = [
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [aws_iam_role.glue_role.arn]
    }
  ])
}

# ---------- Glue job (minimal free-tier) ----------
resource "aws_glue_job" "products_embedding_job" {
  name     = "products-embedding-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${local.bucket_name}/scripts/products_embedding_job.py"
  }

  glue_version       = "4.0"
  number_of_workers  = 2   # smallest serverless size
  worker_type        = "G.1X"
  max_retries        = 0

  default_arguments = {
    "--additional-python-modules" = "awswrangler,pyarrow,langchain_aws,boto3,opensearch-py"
    "--job-language"              = "python"
    "--INPUT_KEY"                 = "clean_data/"
  }
}

# ---------- outputs ----------
output "opensearch_collection_id" {
  value = aws_opensearchserverless_collection.products.id
}

output "glue_role_arn" {
  value = aws_iam_role.glue_role.arn
}
