import boto3
from datetime import datetime, timedelta

logs = boto3.client("logs", region_name="af-south-1")


def query_logs(log_group: str, query: str, hours_back: int = 1) -> dict:
    end = datetime.utcnow()
    start = end - timedelta(hours=hours_back)

    response = logs.start_query(
        logGroupName=log_group,
        startTime=int(start.timestamp()),
        endTime=int(end.timestamp()),
        queryString=query,
        limit=50,
    )
    query_id = response["queryId"]

    import time
    while True:
        result = logs.get_query_results(queryId=query_id)
        if result["status"] in ("Complete", "Failed", "Cancelled"):
            break
        time.sleep(1)

    rows = []
    for r in result.get("results", []):
        rows.append({field["field"]: field["value"] for field in r})

    return {"logGroup": log_group, "query": query, "results": rows}


def get_recent_errors(log_group: str, hours_back: int = 1) -> dict:
    return query_logs(
        log_group=log_group,
        query="fields @timestamp, @message | filter @message like /ERROR|Exception|FATAL/ | sort @timestamp desc | limit 20",
        hours_back=hours_back,
    )
