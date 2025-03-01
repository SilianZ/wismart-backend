from core.env import *
from typing import Any
from sts.sts import Sts
from datetime import datetime
import httpx
import random


def verify_turnstile_token(token: str) -> bool:
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                json={"secret": cloudflare_secret, "response": token},
            )
            data = response.json()
            if data["success"]:
                return True
            else:
                return False
    except Exception:
        return False


def get_temp_cos_security_token(ext: str) -> dict[str, Any] | None:
    def generate_cos_key(ext: str) -> str:
        today = datetime.now().strftime("%Y%m%d")
        random_number = f"{random.randint(0, 999999):06d}"
        file_name = f"{today}_{random_number}{'.' + ext if ext else ''}"
        return f"wismart/{today}/{file_name}"

    cos_key = generate_cos_key(ext)
    credential_option = {
        "duration_seconds": 180,
        "secret_id": cos_secret_id,
        "secret_key": cos_secret_key,
        "bucket": cos_bucket,
        "region": cos_region,
        "policy": {
            "version": "2.0",
            "statement": [
                {
                    "action": [
                        "name/cos:PutObject",
                        "name/cos:InitiateMultipartUpload",
                        "name/cos:ListMultipartUploads",
                        "name/cos:ListParts",
                        "name/cos:UploadPart",
                        "name/cos:CompleteMultipartUpload",
                    ],
                    "effect": "allow",
                    "resource": [cos_key],
                    "condition": {
                        "string_like": {"cos:content-type": "image/*"},
                        "numeric_less_than_equal": {
                            "cos:content-length": 5
                            * 1024
                            * 1024
                        },
                    },
                }
            ],
        },
    }
    try:
        sts = Sts(credential_option)
        response: dict[str, Any] = sts.get_credential()
        print(response)
        return {"Key": cos_key, **response}
    except Exception:
        return None

def get_presigned_url(key: str) -> str | None:
    pass