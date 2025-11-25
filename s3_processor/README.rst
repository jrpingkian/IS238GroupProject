Environment Variables:

EMAIL_BUCKET → S3 bucket where raw emails are stored.

TELEGRAM_SECRET_NAME → AWS Secrets Manager entry holding the Telegram bot token.

OPENAI_SECRET_NAME → AWS Secrets Manager entry holding the OpenAI API key.

DDB_TABLE → DynamoDB table mapping email addresses to Telegram user IDs.


------------------------------------------------------------
AWS Client:

s3 → fetches raw email files.

secrets → retrieves API keys from Secrets Manager.

dynamo → looks up recipient info in DynamoDB.

------------------------------------------------------------
Functions:

get_telegram_token() → loads Telegram bot token from Secrets Manager.

get_openai_key() → loads OpenAI API key.

send_telegram_message(chat_id, text) → sends a message via Telegram Bot API.

call_openai(summary_prompt) → calls a custom OpenAI endpoint (https://openai.is238.upou.io/v1/chat/completions) to generate a summary of the email.

------------------------------------------------------------
Here is our flow diagram:

S3 (new email) → Lambda → Parse email → Extract recipient
       ↓
   DynamoDB lookup → Get Telegram ID
       ↓
   OpenAI → Summarize email
       ↓
   Telegram → Send summary to user



This is a dummy package designed to prevent namesquatting on PyPI. You should install `beautifulsoup4 <https://pypi.python.org/pypi/beautifulsoup4>`_ instead.



