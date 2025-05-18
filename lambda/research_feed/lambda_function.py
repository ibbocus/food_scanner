import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger()
logger.setLevel(logging.INFO)

NCBI_ESEARCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESUMMARY_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

@lru_cache(maxsize=128)
def cached_fetch(url):
    with urllib.request.urlopen(url) as response:
        return response.read().decode()

def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "OPTIONS,GET"
    }

    query_params = event.get("queryStringParameters") or {}
    logger.info("Received query parameters: %s", json.dumps(query_params))

    term = query_params.get("term", "")
    source = query_params.get("source", "pubmed").lower()
    retmax = query_params.get("retmax", "20")
    retstart = query_params.get("retstart", "0")

    if not term:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing search term"}),
            "headers": cors_headers
        }

    esearch_params = {
        "db": source,
        "term": term,
        "retmode": "json",
        "retmax": retmax,
        "retstart": retstart,
        "sort": "pub+date"
    }

    esearch_url = f"{NCBI_ESEARCH_BASE}?{urllib.parse.urlencode(esearch_params)}"
    try:
        esearch_data = json.loads(cached_fetch(esearch_url))
    except Exception as e:
        return {
            "statusCode": 502,
            "body": json.dumps({"error": f"Failed to query ESearch: {str(e)}"}),
            "headers": cors_headers
        }

    id_list = esearch_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return {
            "statusCode": 200,
            "body": json.dumps({"articles": []}),
            "headers": cors_headers
        }

    esummary_params = {
        "db": source,
        "id": ",".join(id_list),
        "retmode": "json"
    }

    esummary_url = f"{NCBI_ESUMMARY_BASE}?{urllib.parse.urlencode(esummary_params)}"
    try:
        esummary_data = json.loads(cached_fetch(esummary_url))
    except Exception as e:
        return {
            "statusCode": 502,
            "body": json.dumps({"error": f"Failed to query ESummary: {str(e)}"}),
            "headers": cors_headers
        }

    result = esummary_data.get("result", {})
    uids = result.get("uids", [])
    articles = []

    for uid in uids:
        item = result.get(uid)
        if not item:
            continue

        pub_date = item.get("pubdate", "")
        try:
            pub_year = int(pub_date[:4])
            if pub_year > datetime.now().year:
                continue
        except:
            pass

        articles.append({
            "id": uid,
            "title": item.get("title"),
            "journal": item.get("fulljournalname"),
            "authors": [a.get("name") for a in item.get("authors", [])],
            "pubdate": pub_date,
            "source": source,
            "url": f"https://www.ncbi.nlm.nih.gov/{source}/articles/{uid}/" if source == "pmc" else f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        })

    return {
        "statusCode": 200,
        "body": json.dumps({"articles": articles}),
        "headers": cors_headers
    }