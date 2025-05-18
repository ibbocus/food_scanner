# modules/glue/variables.tf
variable "source_s3_path" {
  type = string
}

variable "target_s3_path" {
  type = string
}

variable "scripts_bucket" {
  type = string
}

variable "database_name" {
  type = string
}

variable "table_name" {
  type = string
}
