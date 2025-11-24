import os
import json
import boto3
import email
import requests
from email import policy
from email.parser import BytesParser

# Environment variables
S3_BUCKET = os.getenv("EMAIL_BUCKET")
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET_NAME", "/email-bot/telegram")
OPENAI_SECRET = os.getenv("OPENAI_SECRET_NAME", "/email-bot/openai")
DDB_TABLE = os.getenv("DDB_TABLE", "EmailBotAddresses")

# AWS clients
s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")
dynamo = boto3.client("dynamodb")

# ----------------------------------------------------------
# Load Telegram token (correct key name = "bot_token")
# ----------------------------------------------------------
def get_telegram_token():
    resp = secrets.get_secret_value(SecretId=TELEGRAM_SECRET)
    secret_json = json.loads(resp["SecretString"])
    return secret_json["bot_token"]   # ❗ FIXED


# ----------------------------------------------------------
# Load OpenAI key
# ----------------------------------------------------------
def get_openai_key():
    resp = secrets.get_secret_value(SecretId=OPENAI_SECRET)
    secret_json = json.loads(resp["SecretString"])
    return secret_json["OPENAI_API_KEY"]


# ----------------------------------------------------------
# Send Telegram message
# ----------------------------------------------------------
def send_telegram_message(chat_id, text):
    token = get_telegram_token()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------
# Call OpenAI using custom endpoint
# ----------------------------------------------------------
def call_openai(summary_prompt):
    api_key = get_openai_key()
    url = "https://openai.is238.upou.io/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": summary_prompt}
        ]
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    return data["choices"][0]["message"]["content"]


# ----------------------------------------------------------
# Lambda Handler
# ----------------------------------------------------------
def lambda_handler(event, context):

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Processing new email from: s3://{bucket}/{key}")

        # Load raw email
        obj = s3.get_object(Bucket=bucket, Key=key)
        raw_email = obj["Body"].read()

        msg = BytesParser(policy=policy.default).parsebytes(raw_email)
        subject = msg["subject"] or "(No Subject)"

        # ----------------------------------------------------------
        # Extract email body (HTML preferred)
        # ----------------------------------------------------------
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/html":
                    body = part.get_content()
                    break
                elif ctype == "text/plain" and not body:
                    body = part.get_content()
        else:
            body = msg.get_content()

        print("Extracted subject/body.")

        # ----------------------------------------------------------
        # Extract "To" address safely
        # Some emails come like: "John <abc@domain.com>"
        # ----------------------------------------------------------
        raw_to = msg["To"]
        if not raw_to:
            print("No TO header found. Skipping.")
            continue

        print(f"Raw To header: {raw_to}")

        # Extract clean email address
        try:
            to_address = email.utils.parseaddr(raw_to)[1].lower()
        except:
            print(f"Failed to parse TO address: {raw_to}")
            continue

        print(f"Parsed recipient email: {to_address}")

        # ----------------------------------------------------------
        # Lookup in DynamoDB
        # ----------------------------------------------------------
        resp = dynamo.get_item(
            TableName=DDB_TABLE,
            Key={"email_address": {"S": to_address}}
        )

        item = resp.get("Item")

        if not item:
            print(f"No DynamoDB entry for {to_address}. Skipping.")
            continue

        if not item.get("active", {}).get("BOOL", False):
            print(f"{to_address} is inactive. Skipping.")
            continue

        telegram_user_id = item["telegram_user_id"]["S"]

        # ----------------------------------------------------------
        # Call OpenAI summarizer
        # ----------------------------------------------------------
        prompt = (
            f"Summarize this email briefly:\n\n"
            f"Subject: {subject}\n\nBody:\n{body}"
        )

        try:
            print("Calling OpenAI...")
            summary = call_openai(prompt)
            print("Summary generated.")
        except Exception as e:
            print(f"OpenAI error: {e}")
            summary = "Failed generating summary."

        # ----------------------------------------------------------
        # Send Telegram message
        # ----------------------------------------------------------
        try:
            send_telegram_message(
                telegram_user_id,
                f"<b>{subject}</b>\n\n{summary}"
            )
            print("Summary sent to Telegram.")
        except Exception as e:
            print(f"Telegram send error: {e}")

    return {"statusCode": 200, "body": "ok"}
