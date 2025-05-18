# AWS Glue PySpark ETL script (script.py)

import sys
from awsglue.transforms import DropFields
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql.functions import col, explode
from awsglue.job import Job

args = getResolvedOptions(sys.argv,
    ['JOB_NAME','SOURCE_S3_PATH','TARGET_S3_PATH','DATABASE_NAME','TABLE_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Load as DynamicFrame and drop duplicate fields
dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths":[args['SOURCE_S3_PATH']]},
    format="json"
)

dyf_clean = dyf.drop_fields(paths=[
    "generic_name_es",
    "ingredients_text_en",
    "ingredients_text_es",
    "product_name_es"
])

df = dyf_clean.toDF()

# Flatten product struct
prod = df.select(
    col('code').alias('barcode'),
    col('product.product_name').alias('name'),
    col('product.brands').alias('brands'),
    col('product.categories_tags').alias('categories'),
    col('product.allergens_tags').alias('allergens'),
    col('product.nutriments.energy_kcal_100g').alias('energy_kcal_per_100g'),
    col('product.nutriments.fat_100g').alias('fat_per_100g'),
    col('product.nutriments.sugars_100g').alias('sugars_per_100g'),
    col('product.nutriments.proteins_100g').alias('proteins_per_100g'),
    col('product.ingredients').alias('ingredients')
)

# Explode ingredients array into separate rows
ing = prod.withColumn('ingredient', explode('ingredients')) \
     .select(
        'barcode','name','brands','categories','allergens',
        'energy_kcal_per_100g','fat_per_100g','sugars_per_100g','proteins_per_100g',
        col('ingredient.id').alias('ingredient_id'),
        col('ingredient.text').alias('ingredient_name'),
        col('ingredient.percent_estimate').alias('ingredient_pct')
     )

# Write cleaned parquet to S3 and register in Glue Data Catalog
ing.write \
   .format('parquet') \
   .mode('overwrite') \
   .partitionBy('categories') \
   .save(args['TARGET_S3_PATH'])

glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths":[args['TARGET_S3_PATH']]},
    format="parquet"
).toDF() \
 .write \
 .format("glueparquet") \
 .option("path", args['TARGET_S3_PATH']) \
 .saveAsTable(f"{args['DATABASE_NAME']}.{args['TABLE_NAME']}")

job.commit()