import boto3

bedrock_agent = boto3.client("bedrock-agent-runtime", region_name="af-south-1")


def search_runbooks(knowledge_base_id: str, query: str, top_k: int = 3) -> dict:
    response = bedrock_agent.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
    )
    results = [
        {
            "content": r["content"]["text"],
            "score": r["score"],
            "source": r["location"].get("s3Location", {}).get("uri", "unknown"),
        }
        for r in response.get("retrievalResults", [])
    ]
    return {"query": query, "runbooks": results}
