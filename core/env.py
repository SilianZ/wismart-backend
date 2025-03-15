import os

database_url = os.getenv("DATABASE_URL") or "mysql+pymysql://WisMart:Sz4kKbW8M5XNR3bn@154.37.213.151:3306/WisMart"
smtp_server = os.getenv("SMTP_SERVER") or ""
smtp_email = os.getenv("SMTP_EMAIL") or ""
smtp_password = os.getenv("SMTP_PASSWORD") or ""
cloudflare_secret = os.getenv("CLOUDFLARE_SECRET")
cos_bucket = os.getenv("COS_BUCKET")
cos_region = os.getenv("COS_REGION")
cos_secret_id = os.getenv("COS_SECRET_ID")
cos_secret_key = os.getenv("COS_SECRET_KEY")
fallback_img_url = os.getenv("FALLBACK_IMG_URL") or ""
