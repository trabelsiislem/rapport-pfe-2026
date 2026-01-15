How to run the booking_app (development)

Prerequisites
- macOS (you have zsh)
- Python 3.13 (project venv is at `./env`)
- MySQL server running (or update `config/settings.py` to use sqlite for quick local tests)

1) Activate virtualenv

```bash
source ./env/bin/activate
```

2) Install dependencies (only if you changed venv)

```bash
pip install -r requirements.txt
```

3) Export environment variables

# Database (adjust to your local DB)
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=''
export MYSQL_DATABASE=booking_db

# Optional: SMTP settings to actually send emails (Mailtrap example)
export SMTP_HOST=smtp.mailtrap.io
export SMTP_PORT=2525
export SMTP_USER=YOUR_MAILTRAP_USER
export SMTP_PASSWORD=YOUR_MAILTRAP_PASSWORD
export SMTP_USE_TLS=True
export SENDER_EMAIL='itrabelsi507@gmail.com'

4) Apply migrations

```bash
./env/bin/python manage.py migrate
```

5) Create superuser

```bash
./env/bin/python manage.py createsuperuser
```

6) Run the dev server

```bash
./env/bin/python manage.py runserver 127.0.0.1:8000
```

7) Test e-mail sending (script)

```bash
# send a test email to yourself
./env/bin/python scripts/send_test_email.py your@youremail.tld
```

8) Run unit tests

```bash
./env/bin/python manage.py test
```

Troubleshooting
- If `migrate` fails: check DB is reachable and credentials (MYSQL_*) are set. Share the error if you need help.
- If you see emails printed in console (not delivered): the app is using the console backend (DEBUG=True) — set SMTP_* env vars and restart.
- If SMTP fails to authenticate/connect: try different ports (2525 / 587 / 465) and verify SMTP_USER/PASSWORD; run `nc -vz $SMTP_HOST $SMTP_PORT` and `openssl s_client -starttls smtp -crlf -connect $SMTP_HOST:$SMTP_PORT` to debug TLS.

If you want, I can add a `manage.py` command to simplify the test email sending. Please tell me if you'd like that.
