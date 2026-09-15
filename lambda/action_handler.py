import json
import os
from tools.ticket_tool import create_ticket, update_ticket, get_ticket
from tools.infra_tool import get_instance_status, reboot_instance, list_iam_user_access_keys, rotate_iam_access_key
from tools.logs_tool import query_logs, get_recent_errors
from tools.code_tool import scan_repo, apply_fix, read_file
from tools.git_tool import git_status, git_diff, git_commit_and_push


TOOL_MAP = {
    "create_ticket": lambda p: create_ticket(**p),
    "update_ticket": lambda p: update_ticket(**p),
    "get_ticket": lambda p: get_ticket(**p),
    "get_instance_status": lambda p: get_instance_status(**p),
    "reboot_instance": lambda p: reboot_instance(**p),
    "list_iam_user_access_keys": lambda p: list_iam_user_access_keys(**p),
    "rotate_iam_access_key": lambda p: rotate_iam_access_key(**p),
    "query_logs": lambda p: query_logs(**p),
    "get_recent_errors": lambda p: get_recent_errors(**p),
    "search_runbooks": lambda p: {"runbooks": [], "note": "Knowledge base not configured"},
    # Code & Git tools
    "scan_repo": lambda p: scan_repo(**p),
    "apply_fix": lambda p: apply_fix(**p),
    "read_file": lambda p: read_file(**p),
    "git_status": lambda p: git_status(**p),
    "git_diff": lambda p: git_diff(**p),
    "git_commit_and_push": lambda p: git_commit_and_push(**p),
}


def lambda_handler(event, context):
    action_group = event.get("actionGroup")
    function_name = event.get("function")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    if function_name not in TOOL_MAP:
        return _response(action_group, function_name, {"error": f"Unknown function: {function_name}"})

    try:
        result = TOOL_MAP[function_name](parameters)
    except Exception as e:
        result = {"error": str(e)}

    return _response(action_group, function_name, result)


def _response(action_group: str, function_name: str, body: dict) -> dict:
    return {
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseBody": {"TEXT": {"body": json.dumps(body)}}
            },
        }
    }
