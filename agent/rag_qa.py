#!/usr/bin/env python
import os
from dotenv import load_dotenv

from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.chains import RetrievalQA
from langchain import PromptTemplate

from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

# 0. Load config + build signed OpenSearch client
load_dotenv()
REGION      = os.environ.get("AWS_REGION", "eu-west-2")
ENDPOINT    = os.environ["OPENSEARCH_ENDPOINT"]    # host only (no https://)
INDEX_NAME  = os.environ.get("INDEX_NAME", "products-embeddings")

aws_auth = AWS4Auth(
    os.environ["AWS_ACCESS_KEY_ID"],
    os.environ["AWS_SECRET_ACCESS_KEY"],
    REGION,
    "aoss",
    session_token=os.getenv("AWS_SESSION_TOKEN"),
)

client = OpenSearch(
    hosts=[{"host": ENDPOINT, "port": 443}],
    http_auth=aws_auth,
    use_ssl=True,
    verify_certs=True,
    headers={"X-Amz-Content-Sha256": "UNSIGNED-PAYLOAD"},
    connection_class=RequestsHttpConnection,
    timeout=60,
)

# 1. Instantiate embedding model & vector store
embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")

vector_store = OpenSearchVectorSearch(
    opensearch_url=f"https://{ENDPOINT}",
    index_name=INDEX_NAME,
    embedding_function=embeddings,                # pass the Embeddings object itself
    http_auth=aws_auth,
    connection_class=RequestsHttpConnection,
    use_ssl=True,
    verify_certs=True,
    headers={"X-Amz-Content-Sha256": "UNSIGNED-PAYLOAD"},
    is_aoss=True,               # specify Serverless
    vector_field="vector",      # must match your index mapping
    text_field="text",          # must match your index mapping
)

retriever = vector_store.as_retriever(search_kwargs={"k": 4, "vector_field": "vector"})

# 2. Pick your Bedrock chat model
llm = ChatBedrock(
    model_id="amazon.titan-text-lite-v1",
    model_kwargs={"temperature": 0.2}
)

# Custom prompt: use only retrieved database products
prompt_template = """Use ONLY the following product information retrieved from the database to answer the question.
If no retrieved products are relevant, say 'No product found.' Do not invent items.

Retrieved Products:
{context}

Question: {question}
Answer:"""
prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

# 3. Build the RetrievalQA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt},
)

# 4. Run it
if __name__ == "__main__":
    question = input("User question: ")
    # Use invoke() to retrieve both the answer and source documents
    result = qa_chain.invoke({"query": question})
    print("\n--- Answer ---")
    print(result["result"])
    print("\n--- Retrieved Documents ---")
    for doc in result["source_documents"]:
        # Print full document content
        print(f"• Document ID: {doc.metadata.get('id')}")
        print("Content:")
        print(doc.page_content)
        print("-" * 80)