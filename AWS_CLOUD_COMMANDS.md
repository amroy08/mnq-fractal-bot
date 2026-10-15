# ☁️ AWS Cloud Bot Controls (Running 24/7 in the Cloud)

Your bot is running on your **Amazon Web Services (AWS) EC2 Virtual Machine**.
It runs 24/7/365 without your laptop!

- **Server IP:** `3.25.143.94`
- **Instance ID:** `i-0ed76b6c712db0684`
- **SSH Key:** `~/Downloads/mnq-bot-key.pem`
- **Region:** `ap-southeast-2` (Free Tier)

---

## 📜 How to Check Live Logs on AWS

Run this in your Mac Terminal anytime to view live trades from the cloud:
```bash
ssh -i ~/Downloads/mnq-bot-key.pem ubuntu@3.25.143.94 "sudo journalctl -u mnq-bot -f"
```
*(Press `Ctrl + C` to exit log stream).*

---

## 🛑 How to Stop the Cloud Bot
```bash
ssh -i ~/Downloads/mnq-bot-key.pem ubuntu@3.25.143.94 "sudo systemctl stop mnq-bot"
```

## 🟢 How to Restart the Cloud Bot
```bash
ssh -i ~/Downloads/mnq-bot-key.pem ubuntu@3.25.143.94 "sudo systemctl restart mnq-bot"
```

## 🔍 Check Cloud Bot Status
```bash
ssh -i ~/Downloads/mnq-bot-key.pem ubuntu@3.25.143.94 "sudo systemctl status mnq-bot --no-pager"
```
