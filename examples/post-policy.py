"""Genere les champs du formulaire POST S3 pour le Compose local."""
import argparse
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone


def sign(key, message):
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


parser = argparse.ArgumentParser()
parser.add_argument("--key", default="exemple.txt")
parser.add_argument("--bucket", default="bigdata")
parser.add_argument("--access-key", default="admin")
parser.add_argument("--secret-key", default="bigdata-local-secret")
parser.add_argument("--region", default="us-east-1")
args = parser.parse_args()

now = datetime.now(timezone.utc)
day = now.strftime("%Y%m%d")
date = now.strftime("%Y%m%dT%H%M%SZ")
credential = f"{args.access_key}/{day}/{args.region}/s3/aws4_request"
policy = {
    "expiration": (now + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "conditions": [
        {"bucket": args.bucket},
        {"key": args.key},
        {"x-amz-algorithm": "AWS4-HMAC-SHA256"},
        {"x-amz-credential": credential},
        {"x-amz-date": date},
        {"success_action_status": "201"},
    ],
}
encoded = base64.b64encode(json.dumps(policy).encode()).decode("ascii")
key = sign(f"AWS4{args.secret_key}".encode(), day)
for part in (args.region, "s3", "aws4_request"):
    key = sign(key, part)
print(json.dumps({
    "credential": credential,
    "date": date,
    "policy": encoded,
    "signature": sign(key, encoded).hex(),
}))
