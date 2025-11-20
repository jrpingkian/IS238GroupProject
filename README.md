# IS238 – Email Summarization Telegram Bot

This project integrates **Cloudflare Email Router**, **AWS Lambda**, and **Telegram Bot API** to create an automated email summarization system.

---

## 🧩 System Overview


### Cloudflare Email Router


- Cloudflare Email Router – Handles incoming emails and routes them to the system.

---

## ⚙️ AWS Lambda Functions

### 📨 1. Lambda #1 – Gmail Poller
- Logs into Gmail every minute via IMAP (without hardcoding credentials).
- Fetches new emails and stores them in an **S3 Bucket**.
- Implements an **S3 lifecycle policy** for automatic cleanup of stored emails.

---

### 🧠 2. Lambda #2 – S3 Processor
- Monitors the **S3 bucket** for new email uploads.
- Extracts the **email subject and body** (HTML parsing supported).
- Sends content to a **custom OpenAI endpoint** for summarization.
- Sends the generated **email summary** to the corresponding **Telegram user**.
- Generates a **pre-signed S3 URL (7-day validity)** for downloading the raw email.

---

### 🤖 3. Lambda #3 – Telegram Webhook
- Serves as the **Telegram bot’s webhook URL**.
- Handles all user interactions and commands.
  - Generate a new system email address.
  - Deactivate existing addresses.
  - Download raw email via pre-signed URL.

---

## 🗄️ Database
- Stores Telegram user data and associated system-generated email addresses.
- Tracks active/inactive email addresses for each user.

---

## 🧰 Additional Notes
- No EC2 instances are used; the system is fully **serverless** via AWS Lambda.
- Emails with basic HTML formatting are supported.
- File attachments and inline images are **ignored**.
- Expected delay between receiving an email and Telegram notification: **≤ 2 minutes**.

---


## 👥 Contributors


---
