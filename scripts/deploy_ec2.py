"""Deploy da demo do DNA da Máquina numa EC2 (lê credenciais só do ambiente).

Uso::

    export AWS_DEFAULT_REGION=us-west-2 AWS_ACCESS_KEY_ID=... \\
           AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...
    python scripts/deploy_ec2.py .

ATENÇÃO: publica a aplicação SEM LOGIN (portas 80 e 8080 abertas). Só para
demonstração; apague os recursos "dna-maquina-mvp" depois. Ver README.
"""
import json
import os
import sys
import tempfile
import time
import zipfile

import boto3

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
PROJECT = sys.argv[1]
TAG = "dna-maquina-mvp"
EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
                ".ruff_cache", ".kiro", "processed", "cache", "models"}
EXCLUDE_FILES = {".env"}  # segredos nunca vão no pacote

session = boto3.Session(region_name=REGION)
s3 = session.client("s3")
ec2 = session.client("ec2")
ssm = session.client("ssm")
account = session.client("sts").get_caller_identity()["Account"]

# 1) zip do projeto
zip_path = os.path.join(tempfile.gettempdir(), "dna-maquina-deploy.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(PROJECT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS
                   and not (d == "screens" and root.endswith("docs"))]
        for f in files:
            if f in EXCLUDE_FILES or f.startswith(".env."):
                continue
            full = os.path.join(root, f)
            zf.write(full, os.path.relpath(full, PROJECT).replace("\\", "/"))
print(f"zip: {os.path.getsize(zip_path) / 1e6:.1f} MB")

# 2) bucket privado + URL pre-assinada
bucket = f"{TAG}-{account}-{REGION}"
try:
    s3.create_bucket(Bucket=bucket,
                     CreateBucketConfiguration={"LocationConstraint": REGION})
except s3.exceptions.BucketAlreadyOwnedByYou:
    pass
s3.upload_file(zip_path, bucket, "dna.zip")
url = s3.generate_presigned_url("get_object",
                                Params={"Bucket": bucket, "Key": "dna.zip"},
                                ExpiresIn=3600)
print("bucket:", bucket)

# 3) security group: portas 80 e 8080 (sem SSH)
vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [TAG]},
                                            {"Name": "vpc-id", "Values": [vpc]}])["SecurityGroups"]
if sgs:
    sg = sgs[0]["GroupId"]
else:
    sg = ec2.create_security_group(GroupName=TAG, Description="DNA Maquina MVP",
                                   VpcId=vpc)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080,
        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
try:
    ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
except ec2.exceptions.ClientError as e:
    if "Duplicate" not in str(e):
        raise
print("sg:", sg)

# encerra instancias antigas deste deploy
old = [i["InstanceId"] for r in ec2.describe_instances(Filters=[
    {"Name": "tag:Name", "Values": [TAG]},
    {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    for i in r["Instances"]]
if old:
    ec2.terminate_instances(InstanceIds=old)
    print("encerradas:", old)

# 3b) papel IAM so com Bedrock (sobrevive a revogacao da chave do usuario)
iam = session.client("iam")
profile_arn = None
creds_env = ""
try:
    try:
        iam.create_role(RoleName=TAG, AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17", "Statement": [{"Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}))
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    iam.put_role_policy(RoleName=TAG, PolicyName="bedrock-invoke", PolicyDocument=json.dumps({
        "Version": "2012-10-17", "Statement": [{"Effect": "Allow",
        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        "Resource": ["arn:aws:bedrock:*::foundation-model/anthropic.*",
                     "arn:aws:bedrock:*:*:inference-profile/*"]}]}))
    try:
        iam.create_instance_profile(InstanceProfileName=TAG)
        iam.add_role_to_instance_profile(InstanceProfileName=TAG, RoleName=TAG)
        time.sleep(12)  # propagacao do perfil
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    profile_arn = iam.get_instance_profile(InstanceProfileName=TAG)["InstanceProfile"]["Arn"]
    print("papel IAM: ok")
except Exception as e:  # noqa: BLE001
    print("papel IAM indisponivel, usando credencial temporaria:", type(e).__name__)
    creds_env = "".join(f"export {k}='{os.environ[k]}'\n" for k in
                        ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"))

# 4) EC2 Amazon Linux 2023
ami = ssm.get_parameter(
    Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
)["Parameter"]["Value"]
user_data = f"""#!/bin/bash
set -ex
dnf install -y docker unzip
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \\
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
mkdir -p /opt/dna && cd /opt/dna
curl -fsSL "{url}" -o dna.zip
unzip -o dna.zip && rm dna.zip
chmod -R a+rX /opt/dna
cat > compose.port80.yaml <<'EOF'
services:
  frontend:
    ports:
      - "80:8080"
EOF
export DNA_USE_BEDROCK=1 AWS_REGION={REGION}
{creds_env}DNA_UID=1000 DNA_GID=1000 docker compose -f compose.yaml -f compose.port80.yaml up -d --build
"""
def launch(**kw):
    for attempt in range(6):  # perfil IAM recem-criado demora a propagar
        try:
            return ec2.run_instances(**kw)
        except ec2.exceptions.ClientError as e:
            if "instance profile" not in str(e).lower() or attempt == 5:
                raise
            time.sleep(10)


inst = launch(
    ImageId=ami, InstanceType="t3.medium", MinCount=1, MaxCount=1,
    SecurityGroupIds=[sg], UserData=user_data,
    BlockDeviceMappings=[{"DeviceName": "/dev/xvda",
                          "Ebs": {"VolumeSize": 30, "VolumeType": "gp3"}}],
    MetadataOptions={"HttpTokens": "required", "HttpPutResponseHopLimit": 2},
    **({"IamInstanceProfile": {"Arn": profile_arn}} if profile_arn else {}),
    TagSpecifications=[{"ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": TAG}]}],
)["Instances"][0]
iid = inst["InstanceId"]
print("instancia:", iid)
ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
ip = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0].get("PublicIpAddress")
dns = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0].get("PublicDnsName")
os.remove(zip_path)
print(f"URL: http://{ip}  (DNS: http://{dns})")
