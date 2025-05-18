from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat_ws, lit

SOURCE_S3_PATH = 's3a://food-scanner-046873714594/clean_data/'
TARGET_S3_PATH = 's3a://food-scanner-046873714594/clean_data/vectorised/'

spark = SparkSession.builder \
    .appName("LocalVectoriseETL") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .getOrCreate()
df = spark.read.parquet(SOURCE_S3_PATH)
df = df.fillna('')

df = df.withColumn(
    "text_for_embedding",
    concat_ws("\n",
        concat_ws(": ", lit("Product"), col("product_name")),
        concat_ws(": ", lit("Brand"), col("brands_tags")),
        concat_ws(": ", lit("Categories"), col("categories")),
        concat_ws(": ", lit("Allergens"), col("allergens_tags")),
        concat_ws(": ", lit("Ingredients"), col("ingredients_text")),
        concat_ws(": ", lit("Energy (kcal/100g)"), col("energy_kcal_100g")),
        concat_ws(": ", lit("Fat (g/100g)"), col("fat_100g")),
        concat_ws(": ", lit("Sugars (g/100g)"), col("sugars_100g")),
        concat_ws(": ", lit("Proteins (g/100g)"), col("proteins_100g"))
    )
)

df.write.mode("overwrite").parquet(TARGET_S3_PATH)