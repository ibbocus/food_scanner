import os
import boto3
from dotenv import load_dotenv
load_dotenv()
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.llms import Bedrock
from langchain.chains import RetrievalQA

# configuration
region = os.getenv("AWS_REGION", "eu-west-2")
opensearch_host = os.getenv("OPENSEARCH_ENDPOINT")
if not opensearch_host:
    raise RuntimeError("Environment variable OPENSEARCH_ENDPOINT must be set")
index_name = os.getenv("COLLECTION_NAME", "products-embeddings")

# OpenSearch client with SigV4
session = boto3.Session(region_name=region)
creds   = session.get_credentials().get_frozen_credentials()
auth    = AWSV4SignerAuth(creds, region)

client = OpenSearch(
    hosts               = [{"host": opensearch_host, "port": 443}],
    http_auth           = auth,
    use_ssl             = True,
    verify_certs        = True,
    connection_class    = RequestsHttpConnection
)

# embeddings & vectorstore
embeddings = BedrockEmbeddings(
    model_id    = "amazon.titan-embed-text-v2:0",
    region_name = region
)
vectorstore = OpenSearchVectorSearch(
    opensearch_url     = f"https://{opensearch_host}",
    index_name         = index_name,
    embedding_function = embeddings,
    client             = client
)

# LLM
llm = Bedrock(
    model_id    = "amazon.titan-text-002",
    region_name = region
)

# RetrievalQA chain
qa = RetrievalQA.from_chain_type(
    llm          = llm,
    chain_type   = "stuff",
    retriever    = vectorstore.as_retriever()
)

# interactive loop
if __name__ == "__main__":
    print("RAG agent ready. Enter your questions:")
    while True:
        query = input(">>> ")
        if not query.strip():
            break
        answer = qa.run(query)
        print(answer)