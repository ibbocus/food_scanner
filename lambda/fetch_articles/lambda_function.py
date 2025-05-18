import json
import urllib.parse
import urllib.request
import logging

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    query_params = event.get("queryStringParameters") or {}
    logger.info("Received event: %s", json.dumps(event))
    logger.info("Parsed query parameters: %s", json.dumps(query_params))
    term = query_params.get("term", "")
    retmax = query_params.get("retmax", "10")
    db = "pubmed"

    year_from = query_params.get("yearFrom")
    year_to = query_params.get("yearTo")
    journal_type = query_params.get("journalType")
    full_text_only = query_params.get("fullTextOnly", "").lower() == "true"
    sort_by = query_params.get("sortBy", "").lower()

    if not term:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing search term"}),
            "headers": cors_headers
        }

    term_clauses = [term]
    if year_from and year_to:
        term_clauses.append(f"{year_from}:{year_to}[pdat]")
    elif year_from:
        term_clauses.append(f"{year_from}[pdat]")
    elif year_to:
        term_clauses.append(f"{year_to}[pdat]")

    if journal_type and journal_type != "all":
        term_clauses.append(f"{journal_type}[journal]")

    if full_text_only:
        term_clauses.append("full text[sb]")

    params = {
        "db": db,
        "term": "".join(term_clauses),
        "retmode": "json",
        "retmax": retmax,
        "usehistory": "y"
    }

    if sort_by == "most recent":
        params["sort"] = "pub+date"

    url = f"{NCBI_BASE_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": cors_headers
        }

    # EFetch support
    if query_params.get("fetch", "false").lower() == "true":
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No IDs found to fetch"}),
                "headers": cors_headers
            }

        efetch_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        efetch_params = {
            "db": db,
            "id": ",".join(ids),
            "retmode": "xml"
        }

        efetch_url = f"{efetch_base}?{urllib.parse.urlencode(efetch_params)}"
        try:
            with urllib.request.urlopen(efetch_url) as efetch_response:
                efetch_data = efetch_response.read().decode()
                return {
                    "statusCode": 200,
                    "body": efetch_data,
                    "headers": {
                        "Content-Type": "application/xml",
                        **cors_headers
                    }
                }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"EFetch failed: {str(e)}"}),
                "headers": cors_headers
            }

    result = {
        "query": params["term"],
        "count": data.get("esearchresult", {}).get("count"),
        "ids": data.get("esearchresult", {}).get("idlist", []),
        "webenv": data.get("esearchresult", {}).get("webenv"),
        "querykey": data.get("esearchresult", {}).get("querykey"),
    }

    return {
        "statusCode": 200,
        "body": json.dumps(result),
        "headers": cors_headers
    }