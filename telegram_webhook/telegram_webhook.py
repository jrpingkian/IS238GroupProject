# telegram_webhook.py
import os
import json
import boto3
import uuid
from datetime import datetime
from urllib.parse import unquote_plus

secrets = boto3.client("secretsmanager")
dynamo = boto3.client("dynamodb")

DDB_TABLE = os.getenv("DDB_TABLE", "EmailBotAddresses")
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET_NAME", "/email-bot/telegram")
COMPANY_DOMAIN = os.getenv("COMPANY_DOMAIN", "smdelfin-up.me")

def get_telegram_token():
    resp = secrets.get_secret_value(SecretId=TELEGRAM_SECRET)
    return json.loads(resp["SecretString"])["bot_token"]

def lambda_handler(event, context):
    # event is HTTP POST from Telegram (API Gateway or Lambda Function URL)
    body = event.get("body")
    if not body:
        return {"statusCode": 400, "body": "no body"}
    update = json.loads(body)
    # detect message
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if text and text.strip().lower().startswith("/start"):
            return respond_text(chat_id, "Welcome! Use /new to create a new email address, or /list to view addresses.")
        if text and text.strip().lower().startswith("/new"):
            return handle_new_address(chat_id)
        if text and text.strip().lower().startswith("/list"):
            return handle_list_addresses(chat_id)
        # handle other incoming messages or ignore
        return respond_text(chat_id, "Unknown command. Use /new or /list.")
    # detect callback_query (button presses)
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        chat_id = cq["from"]["id"]
        message_id = cq["message"]["message_id"]
        # parse callback_data
        parts = data.split("|")
        action = parts[0]
        if action == "deactivate":
            email_addr = parts[1]
            # send confirmation keyboard
            return send_confirm_deactivate(chat_id, message_id, email_addr)
        if action == "confirm_deactivate":
            email_addr = parts[1]
            return perform_deactivate(chat_id, message_id, email_addr)
        if action == "cancel_deactivate":
            return answer_callback(cq["id"], "Cancelled")
    return {"statusCode": 200, "body": ""}

## helper functions interacting with Telegram API directly
def post_telegram_api(method, payload):
    import requests
    token = get_telegram_token()  # Loads from Secrets Manager
    url = f"https://api.telegram.org/bot{token}/{method}"
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def respond_text(chat_id, text):
    resp = post_telegram_api("sendMessage", {"chat_id": chat_id, "text": text})
    return {"statusCode": 200, "body": "ok"}

def handle_new_address(chat_id):
    
    # generate random local-part
    local = uuid.uuid4().hex[:10]
    email_addr = f"{local}@{COMPANY_DOMAIN}"
    now = datetime.utcnow().isoformat() + "Z"
    # write to DynamoDB
    dynamo.put_item(
        TableName=DDB_TABLE,
        Item={
            "email_address": {"S": email_addr},
            "telegram_user_id": {"S": str(chat_id)},
            "created_at": {"S": now},
            "active": {"BOOL": True},
            "usage_count": {"N": "0"}
        },
        ConditionExpression="attribute_not_exists(email_address)"
    )
    # reply with instructions
    message = (
        f"✅ Created address: <b>{email_addr}</b>\n\n"
        f"Forward emails you want summarized to this address.\n\n"
        f"Use /list to see and manage your addresses."
    )
    post_telegram_api("sendMessage", {"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    return {"statusCode": 200, "body": "created"}


def handle_list_addresses(chat_id):
    # scan (filter by telegram_user_id)
    resp = dynamo.scan(TableName=DDB_TABLE, FilterExpression="telegram_user_id = :u", ExpressionAttributeValues={":u": {"S": str(chat_id)}})
    items = resp.get("Items", [])
    if not items:
        post_telegram_api("sendMessage", {"chat_id": chat_id, "text": "You have no addresses. Use /new to create one."})
        return {"statusCode": 200, "body": "no addresses"}
    text_lines = []
    for it in items:
        addr = it["email_address"]["S"]
        active = it.get("active", {"BOOL": True})["BOOL"]
        last = it.get("last_email_at", {}).get("S", "never")
        text_lines.append(f"{addr} — {'active' if active else 'inactive'} — last: {last}")
    post_telegram_api("sendMessage", {"chat_id": chat_id, "text": "\n".join(text_lines)})
    return {"statusCode": 200, "body": "listed"}
