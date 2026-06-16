import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import requests
except Exception as e:
    print(json.dumps({"error": "requests_missing", "detail": str(e)}))
    raise SystemExit(2)

k = os.environ.get('EMAIL_API_KEY')
if not k:
    print(json.dumps({"error": "no_api_key"}))
    raise SystemExit(3)

recipient = 'osartech3@gmail.com'
sender = os.environ.get('EMAIL_API_FROM') or os.environ.get('SMTP_FROM') or 'noreply@example.com'
url = 'https://api.brevo.com/v3/smtp/email'
payload = {
    'sender': {'email': sender},
    'to': [{'email': recipient}],
    'subject': 'SchoolOS API test',
    'textContent': 'This is a test email sent via Brevo API from SchoolOS.'
}
headers = {
    'api-key': k,
    'Content-Type': 'application/json'
}
try:
    resp = requests.post(url, json=payload, headers=headers, timeout=int(os.environ.get('EMAIL_API_TIMEOUT', '10')))
    out = {'status_code': resp.status_code, 'ok': resp.ok}
    # include limited response text for debugging, truncated
    text = resp.text or ''
    out['response_text'] = text[:2000]
    print(json.dumps(out))
except Exception as e:
    print(json.dumps({'error': 'request_exception', 'detail': str(e)}))
    raise SystemExit(4)
