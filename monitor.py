import json
import os
import hashlib
import smtplib
from email.message import EmailMessage
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ISRO_URL = "https://www.isro.gov.in/ISRO_EN/ViewAllOpportunities.html"
SEEN_FILE = "seen.json"

ISRO_KEYWORDS = [
    "scientist/engineer 'sc'",
    "scientist/engineer 'sd'",
    "scientist/engineer-sc",
    "scientist/engineer-sd",
]

HEADERS = {
    "User-Agent": "ISRO-DRDO-Alert/1.0"
}


def get_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def check_isro():
    response = requests.get(
        ISRO_URL,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    matches = []

    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())

        if not title:
            continue

        lower = title.lower()

        if any(keyword in lower for keyword in ISRO_KEYWORDS):
            url = urljoin(ISRO_URL, link["href"])

            key = hashlib.sha256(
                f"ISRO|{title}|{url}".encode()
            ).hexdigest()

            matches.append({
                "id": key,
                "organization": "ISRO",
                "title": title,
                "url": url
            })

    return matches


def send_email(new_items):
    sender = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["ALERT_TO"]

    message = EmailMessage()

    message["Subject"] = (
        f"🚨 NEW ISRO SC/SD NOTIFICATION "
        f"({len(new_items)})"
    )

    message["From"] = sender
    message["To"] = recipient

    body = "NEW ISRO RECRUITMENT DETECTED\n\n"

    for item in new_items:
        body += (
            f"Organization: {item['organization']}\n"
            f"Post/Notification: {item['title']}\n"
            f"Official link: {item['url']}\n\n"
        )

    message.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)


def main():

    seen = get_seen()

    current = check_isro()

    new_items = [
        item for item in current
        if item["id"] not in seen
    ]

    for item in current:
        seen.add(item["id"])

    save_seen(seen)

    if new_items:
        print("NEW NOTIFICATION FOUND!")

        for item in new_items:
            print(item["title"])
            print(item["url"])

        send_email(new_items)

    else:
        print("No new notification.")


if __name__ == "__main__":
    main()
