#!/bin/bash

# === CONFIGURATION ===
LOCAL_SCRIPT_PATH="glue/products_embedding_job.py"
S3_BUCKET="food-scanner-046873714594"
S3_SCRIPT_PREFIX="glue-scripts"
S3_SCRIPT_URI="s3://${S3_BUCKET}/${S3_SCRIPT_PREFIX}/${LOCAL_SCRIPT_PATH}"

# === PARAMETERS FOR GLUE JOB ===
GLUE_JOB_NAME="ProductsEmbeddingJob"
ROLE_NAME="AWSGlueServiceRole"  # Update if your IAM role has a different name
PYTHON_VERSION="3.9"

# === 1. Upload your script to S3 ===
echo "Uploading script to S3..."
aws s3 cp "$LOCAL_SCRIPT_PATH" "$S3_SCRIPT_URI"

# === 2. Output job creation command ===
echo ""
echo "To create the Glue Python Shell job, run the following AWS CLI command:"
echo ""
cat <<EOF
aws glue create-job \\
  --name ${GLUE_JOB_NAME} \\
  --role ${ROLE_NAME} \\
  --command '{"Name": "pythonshell", "ScriptLocation": "${S3_SCRIPT_URI}", "PythonVersion": "${PYTHON_VERSION}"}' \\
  --default-arguments '{
    "--bucket_name": "${S3_BUCKET}",
    "--input_key": "clean_data/vectorised/",
    "--region": "eu-west-2",
    "--opensearch_endpoint": "k1w9nv2qspg7rk5c5aif.eu-west-2.aoss.amazonaws.com",
    "--collection_name": "products-embeddings",
    "--additional-python-modules": "langchain_aws,opensearch-py,pyarrow,tqdm"
  }' \\
  --max-capacity 2.0
EOF

echo ""
echo "✅ Upload complete. Copy the above CLI command to create your Glue job."