# AeroResolve AI — VPS Deployment Guide

Step-by-step guide to deploy this FastAPI application to a Linux VPS with Nginx and a systemd service.

---

## 0. Assumptions

- VPS running **Ubuntu 22.04 / 24.04**.
- You have SSH access and a domain or subdomain pointing to the VPS IP.
- You have a **Google Gemini API key**.
- The app uses in-memory storage, so data resets on service restart. For production persistence, replace [`backend/database.py`](backend/database.py:12) with a real database later.

---

## 1. Prepare the project locally

Make sure these files exist in the project root before uploading:

- [`main.py`](main.py:1) — FastAPI entrypoint
- [`requirements.txt`](requirements.txt:1) — Python dependencies
- [`backend/`](backend) — application package
- [`static/`](static) — frontend assets

Create a `.gitignore` if you plan to use Git:

```text
__pycache__/
*.pyc
.env
.venv/
```

---

## 2. Upload the code to the VPS

Choose one method.

### Option A — Git (recommended)

```bash
git init
git add .
git commit -m "AeroResolve AI deployment"
git remote add origin git@github.com:YOUR_USER/YOUR_REPO.git
git push -u origin main
```

### Option B — rsync / SCP directly

From your local machine:

```bash
rsync -av --exclude '__pycache__' --exclude '.venv' ./ USER@VPS_IP:/opt/aeroresolve
```

---

## 3. Connect to the VPS and install system packages

```bash
ssh USER@VPS_IP
```

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx
```

---

## 4. Place the project on the server

```bash
sudo mkdir -p /opt/aeroresolve
sudo chown -R $USER:$USER /opt/aeroresolve
cd /opt/aeroresolve
```

Then clone or copy the project into `/opt/aeroresolve`.

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git .
```

---

## 5. Create a virtual environment and install dependencies

```bash
cd /opt/aeroresolve
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Configure environment variables

Create a systemd environment file for secrets:

```bash
sudo mkdir -p /etc/aeroresolve
sudo nano /etc/aeroresolve/env
```

Add:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

The app already reads `GEMINI_API_KEY` from the environment in [`backend/config.py`](backend/config.py:7).

---

## 7. Smoke-test the app before creating the service

```bash
cd /opt/aeroresolve
source .venv/bin/activate
python main.py
```

Open a browser to `http://VPS_IP:8000`. Confirm the page loads, then press `Ctrl+C`.

---

## 8. Create the systemd service

```bash
sudo nano /etc/systemd/system/aeroresolve.service
```

Paste:

```ini
[Unit]
Description=AeroResolve AI FastAPI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/aeroresolve
EnvironmentFile=/etc/aeroresolve/env
ExecStart=/opt/aeroresolve/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Fix ownership and start the service:

```bash
sudo chown -R www-data:www-data /opt/aeroresolve
sudo systemctl daemon-reload
sudo systemctl enable aeroresolve
sudo systemctl start aeroresolve
sudo systemctl status aeroresolve
```

---

## 9. Configure Nginx reverse proxy

Create an Nginx site:

```bash
sudo nano /etc/nginx/sites-available/aeroresolve
```

Paste:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/aeroresolve /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 10. Enable HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Follow the prompts. Certbot will update the Nginx config automatically.

---

## 11. Configure the firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## 12. Final verification

| Check | Command |
| :--- | :--- |
| Service status | `sudo systemctl status aeroresolve` |
| App logs | `sudo journalctl -u aeroresolve -f` |
| Local app check | `curl -s http://127.0.0.1:8000/api/info` |
| Public app check | Open `https://your-domain.com` |

---

## 13. Useful production commands

```bash
# Restart the app after code changes
sudo systemctl restart aeroresolve

# View live logs
sudo journalctl -u aeroresolve -f

# Test the API through Nginx
curl -s https://your-domain.com/api/tickets?role=admin
```

---

## 14. Production considerations

1. The in-memory [`Database`](backend/database.py:12) loses all state on restart — swap it for SQLite/PostgreSQL for real persistence.
2. The `role` flag access model is for demo purposes — add real admin authentication before public use.
3. Store `GEMINI_API_KEY` only in `/etc/aeroresolve/env`, never in the repository.
4. Keep [`backend/config.py`](backend/config.py:7) reading from environment variables; remove any hardcoded fallback key before production.
