import httpx
import os

secret = os.getenv("CLOUDFLARE_SECRET")


def verify_turnstile_token(token: str) -> bool:
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                json={"secret": secret, "response": token},
            )
            data = response.json()
            if data["success"]:
                return True
            else:
                return False
    except Exception:
        return False
