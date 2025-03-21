import dotenv
import os

dotenv.load_dotenv()

database_url = os.getenv("DATABASE_URL") or ""
smtp_server = os.getenv("SMTP_SERVER") or ""
smtp_email = os.getenv("SMTP_EMAIL") or ""
smtp_password = os.getenv("SMTP_PASSWORD") or ""
cloudflare_secret = os.getenv("CLOUDFLARE_SECRET")
cos_bucket = os.getenv("COS_BUCKET")
cos_region = os.getenv("COS_REGION")
cos_secret_id = os.getenv("COS_SECRET_ID")
cos_secret_key = os.getenv("COS_SECRET_KEY")
