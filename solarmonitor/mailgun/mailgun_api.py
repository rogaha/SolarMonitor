import requests


def send_email(sender, subject, to, text):
    return requests.post(
        "https://api.mailgun.net/v3/solardatapros.com/messages",
        auth=("api", "key-e3bfd2daee0cab79737c792954d54b12"),
        data={"from": sender,
              "to": to,
              "bcc": 'brad@epirtle.com',
              "subject": subject,
              "text": text})

def send_html_email(sender, subject, to, html):
    return requests.post(
        "https://api.mailgun.net/v3/solardatapros.com/messages",
        auth=("api", "key-e3bfd2daee0cab79737c792954d54b12"),
        data={"from": sender,
              "to": to,
              "bcc": 'brad@epirtle.com',
              "subject": subject,
              "html": html})
