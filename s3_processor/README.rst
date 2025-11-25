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


------------------------------------------------------------

The program takes the subject line and the body text of the email it just read..

It then creates a simple instruction (called a prompt) that says something like: 
“Summarize this email briefly: Subject: … Body: …”

That instruction is sent to OpenAI’s AI service (basically, a smart text‑summarizing robot).,

The AI reads the email content and produces a short,  easy‑to‑understand summary.

If something goes wrong (like the AI service is unavailable),  the program just says “Failed generating summary.” instead of crashing.


