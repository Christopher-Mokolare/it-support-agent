import boto3
import uuid
from agent.instructions import AGENT_INSTRUCTION

bedrock = boto3.client("bedrock-agent", region_name="af-south-1")
runtime = boto3.client("bedrock-agent-runtime", region_name="af-south-1")


def create_agent(role_arn: str, knowledge_base_id: str) -> dict:
    response = bedrock.create_agent(
        agentName="it-support-agent",
        agentResourceRoleArn=role_arn,
        foundationModel="anthropic.claude-3-5-sonnet-20241022-v2:0",
        instruction=AGENT_INSTRUCTION,
        description="AI IT Support Engineer that owns the IT support lane end-to-end",
    )
    agent_id = response["agent"]["agentId"]

    if knowledge_base_id:
        bedrock.associate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion="DRAFT",
            knowledgeBaseId=knowledge_base_id,
            description="Internal runbooks and IT documentation",
            knowledgeBaseState="ENABLED",
        )

    import time; time.sleep(5)
    bedrock.prepare_agent(agentId=agent_id)
    return {"agentId": agent_id}


def invoke_agent(agent_id: str, alias_id: str, message: str, session_id: str = None) -> str:
    session_id = session_id or str(uuid.uuid4())
    response = runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=message,
    )

    output = ""
    for event in response["completion"]:
        print("EVENT:", list(event.keys()))
        if "chunk" in event:
            output += event["chunk"]["bytes"].decode("utf-8")
    print("AGENT OUTPUT:", repr(output))
    return output or "(no response from agent)"
