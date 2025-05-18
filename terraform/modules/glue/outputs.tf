output "glue_crawler_name" {
  value = aws_glue_crawler.openfoodfacts.name
}

output "glue_job_name" {
  value = aws_glue_job.openfoodfacts_etl.name
}
