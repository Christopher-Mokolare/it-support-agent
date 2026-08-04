import boto3

ec2 = boto3.client("ec2", region_name="af-south-1")
iam = boto3.client("iam", region_name="af-south-1")


def get_instance_status(instance_id: str) -> dict:
    response = ec2.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
    statuses = response.get("InstanceStatuses", [])
    if not statuses:
        return {"error": "Instance not found"}
    s = statuses[0]
    return {
        "instanceId": instance_id,
        "state": s["InstanceState"]["Name"],
        "systemStatus": s["SystemStatus"]["Status"],
        "instanceStatus": s["InstanceStatus"]["Status"],
    }


def reboot_instance(instance_id: str) -> dict:
    ec2.reboot_instances(InstanceIds=[instance_id])
    return {"instanceId": instance_id, "action": "reboot", "status": "initiated"}


def list_iam_user_access_keys(username: str) -> dict:
    response = iam.list_access_keys(UserName=username)
    keys = [
        {"accessKeyId": k["AccessKeyId"], "status": k["Status"]}
        for k in response["AccessKeyMetadata"]
    ]
    return {"username": username, "accessKeys": keys}


def rotate_iam_access_key(username: str, old_key_id: str) -> dict:
    iam.update_access_key(UserName=username, AccessKeyId=old_key_id, Status="Inactive")
    new_key = iam.create_access_key(UserName=username)["AccessKey"]
    return {
        "username": username,
        "oldKeyDeactivated": old_key_id,
        "newAccessKeyId": new_key["AccessKeyId"],
        # SecretAccessKey shown once — agent should relay securely to user
        "newSecretAccessKey": new_key["SecretAccessKey"],
    }


def list_security_groups(vpc_id: str) -> dict:
    response = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    groups = [
        {"groupId": g["GroupId"], "groupName": g["GroupName"], "description": g["Description"]}
        for g in response["SecurityGroups"]
    ]
    return {"vpcId": vpc_id, "securityGroups": groups}
