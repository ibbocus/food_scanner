# main.tf

module "glue" {
  source           = "./modules/glue"
  source_s3_path   = "s3://food-scanner-046873714594/db/"
  target_s3_path   = "s3://food-scanner-046873714594"
  scripts_bucket   = "s3://food-scanner-046873714594"
  database_name    = "openfoodfacts_db"
  table_name       = "db"
}

module "receipt_scanner" {
  source = "./modules/receipt_scanner"
  depends_on = [ module.apigateway ]
}


module "apigateway" {
  source = "./modules/apigateway"
}