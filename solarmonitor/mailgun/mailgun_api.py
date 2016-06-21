import requests


def send_email(sender, subject, to, text):
    return requests.post(
        "https://api.mailgun.net/v3/app618ef831f75f4a2eb15e3f08f18d09fe.mailgun.org/messages",
        auth=("api", "key-e3bfd2daee0cab79737c792954d54b12"),
        data={"from": sender,
              "to": to,
              "subject": subject,
              "text": text})
