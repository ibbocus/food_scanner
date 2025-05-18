# modules/glue/glue.tf

resource "aws_glue_crawler" "openfoodfacts" {
  name          = "openfoodfacts-crawler"
  database_name = aws_glue_catalog_database.openfoodfacts.name
  role          = aws_iam_role.glue_service_role.arn

  s3_target {
    path = var.source_s3_path   
  }

  classifiers = [ aws_glue_classifier.jsonl.name ]

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DEPRECATE_IN_DATABASE"
  }
}

resource "aws_glue_job" "openfoodfacts_etl" {
  name              = "openfoodfacts-etl"
  role_arn          = aws_iam_role.glue_service_role.arn
  glue_version      = "3.0"
  number_of_workers = 10
  worker_type       = "G.1X"

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "${var.scripts_bucket}/food_etl.py"
  }

  default_arguments = {
    "--SOURCE_S3_PATH" = var.source_s3_path
    "--TARGET_S3_PATH" = var.target_s3_path
    "--DATABASE_NAME"  = var.database_name
    "--TABLE_NAME"     = var.table_name
  }

  max_retries = 1
}

resource "aws_glue_catalog_database" "openfoodfacts" {
  name = var.database_name

  description = "OpenFoodFacts cleaned data"
  parameters = {
    created_by = "terraform"
  }
}

resource "aws_glue_classifier" "jsonl" {
  name = "openfoodfacts-jsonl"

  json_classifier {
    json_path = "$"
  }
}
