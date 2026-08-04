import boto3
import os

s3 = boto3.client("s3", region_name="af-south-1")
bedrock_agent = boto3.client("bedrock-agent", region_name="af-south-1")


def create_knowledge_base(role_arn: str, bucket_name: str, collection_arn: str) -> dict:
    response = bedrock_agent.create_knowledge_base(
        name="it-support-runbooks",
        description="Internal IT runbooks, incident history, and documentation",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": "arn:aws:bedrock:af-south-1::foundation-model/amazon.titan-embed-text-v2:0"
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": collection_arn,
                "vectorIndexName": "it-support-index",
                "fieldMapping": {
                    "vectorField": "embedding",
                    "textField": "text",
                    "metadataField": "metadata",
                },
            },
        },
    )
    kb_id = response["knowledgeBase"]["knowledgeBaseId"]

    # attach S3 data source
    bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name="runbooks-s3",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {"bucketArn": f"arn:aws:s3:::{bucket_name}"},
        },
    )

    return {"knowledgeBaseId": kb_id}


def sync_knowledge_base(knowledge_base_id: str, data_source_id: str) -> dict:
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id,
    )
    return {"ingestionJobId": response["ingestionJob"]["ingestionJobId"], "status": "started"}
