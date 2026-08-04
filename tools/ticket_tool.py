import boto3
import json
from datetime import datetime

dynamodb = boto3.resource("dynamodb", region_name="af-south-1")
table = dynamodb.Table("it-support-tickets")


def create_ticket(title: str, description: str, severity: str, reporter: str) -> dict:
    ticket_id = f"TKT-{int(datetime.utcnow().timestamp())}"
    item = {
        "ticketId": ticket_id,
        "title": title,
        "description": description,
        "severity": severity,  # low | medium | high | critical
        "reporter": reporter,
        "status": "open",
        "createdAt": datetime.utcnow().isoformat(),
        "actions": [],
    }
    table.put_item(Item=item)
    return {"ticketId": ticket_id, "status": "open"}


def update_ticket(ticket_id: str, status: str, action_taken: str) -> dict:
    table.update_item(
        Key={"ticketId": ticket_id},
        UpdateExpression="SET #s = :s, actions = list_append(actions, :a), updatedAt = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": status,
            ":a": [{"action": action_taken, "timestamp": datetime.utcnow().isoformat()}],
            ":t": datetime.utcnow().isoformat(),
        },
    )
    return {"ticketId": ticket_id, "status": status}


def get_ticket(ticket_id: str) -> dict:
    response = table.get_item(Key={"ticketId": ticket_id})
    return response.get("Item", {})
