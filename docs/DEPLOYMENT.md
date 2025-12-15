# MoodMend Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Database Management](#database-management)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- (Optional) Docker and Docker Compose

---

## Local Development

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/moodmend.git
cd moodmend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Initialize Database
```bash
python init_test_data.py
```

### 5. Start Backend Server
```bash
cd src/backend
python moodmend_backend.py
```

The backend will be available at `http://localhost:3000`

### 6. Open Frontend
Open `src/frontend/moodmend_ui_demo.html` in your web browser.

---

## Docker Deployment

### Quick Start
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Manual Docker Build
```bash
# Build image
docker build -t moodmend:latest .

# Run container
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  --name moodmend \
  moodmend:latest
```

---

## Production Deployment

### Option 1: Heroku

1. **Install Heroku CLI**
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku
   ```

2. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set DEBUG=False
   heroku config:set SECRET_KEY=your-secret-key
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

### Option 2: DigitalOcean

1. **Create Droplet** (Ubuntu 22.04)

2. **SSH into Server**
   ```bash
   ssh root@your-server-ip
   ```

3. **Install Dependencies**
   ```bash
   apt update
   apt install python3-pip python3-venv nginx
   ```

4. **Clone Repository**
   ```bash
   cd /var/www
   git clone https://github.com/yourusername/moodmend.git
   cd moodmend
   ```

5. **Set Up Python Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration
   ```

7. **Set Up Systemd Service**
   Create `/etc/systemd/system/moodmend.service`:
   ```ini
   [Unit]
   Description=MoodMend Backend Service
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/moodmend/src/backend
   Environment="PATH=/var/www/moodmend/venv/bin"
   ExecStart=/var/www/moodmend/venv/bin/python moodmend_backend.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

8. **Start Service**
   ```bash
   systemctl daemon-reload
   systemctl start moodmend
   systemctl enable moodmend
   ```

9. **Configure Nginx**
   Create `/etc/nginx/sites-available/moodmend`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           root /var/www/moodmend/src/frontend;
           index moodmend_ui_demo.html;
       }

       location /api {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

10. **Enable Site**
    ```bash
    ln -s /etc/nginx/sites-available/moodmend /etc/nginx/sites-enabled/
    nginx -t
    systemctl restart nginx
    ```

### Option 3: AWS EC2

Similar to DigitalOcean, but:
1. Launch EC2 instance (t2.micro for testing)
2. Configure Security Groups (allow ports 80, 443, 22)
3. Follow DigitalOcean steps above

---

## Environment Configuration

### Required Variables
```env
PORT=3000
HOST=0.0.0.0
DEBUG=False  # Set to False in production
DATABASE_PATH=/var/lib/moodmend/moodmend.db
SECRET_KEY=your-very-secret-key-here
```

### Optional Variables
```env
LOG_LEVEL=INFO
LOG_FILE=/var/log/moodmend/moodmend.log
CORS_ORIGINS=https://yourdomain.com
```

---

## Database Management

### Backup Database
```bash
python scripts/backup_database.py
```

Backups are stored in `backups/` directory with timestamps.

### Restore Database
```bash
python scripts/restore_database.py
```

### Automated Backups
Set up a cron job:
```bash
crontab -e
```

Add:
```
0 2 * * * cd /var/www/moodmend && python scripts/backup_database.py
```

---

## Monitoring & Maintenance

### Health Check
```bash
curl http://localhost:3000/health
```

### View Logs
```bash
# Application logs
tail -f moodmend.log

# System service logs
journalctl -u moodmend -f
```

### Database Statistics
```bash
sqlite3 src/backend/moodmend.db "SELECT COUNT(*) FROM users;"
sqlite3 src/backend/moodmend.db "SELECT COUNT(*) FROM logs;"
```

---

## SSL/HTTPS Setup

### Using Let's Encrypt (Recommended)
```bash
# Install Certbot
apt install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

---

## Troubleshooting

### Backend Won't Start
- Check if port 3000 is already in use: `lsof -i :3000`
- Verify database file exists and has correct permissions
- Check logs for error messages

### Frontend Can't Connect to Backend
- Verify backend is running: `curl http://localhost:3000/health`
- Check CORS configuration in `.env`
- Verify API endpoint URLs in frontend code

### Database Errors
- Check database file permissions
- Verify database path in `.env`
- Try restoring from backup

---

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Set DEBUG=False in production
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (UFW)
- [ ] Set up automated backups
- [ ] Restrict database file permissions
- [ ] Use strong passwords for user accounts
- [ ] Keep dependencies updated

---

## Performance Optimization

### Database
- Indexes are already created for common queries
- Consider vacuuming database monthly: `sqlite3 moodmend.db "VACUUM;"`

### Backend
- Use gunicorn for production: `gunicorn -w 4 -b 0.0.0.0:3000 moodmend_backend:app`
- Enable gzip compression in Nginx

### Frontend
- Minify JavaScript and CSS
- Enable browser caching
- Use CDN for static assets

---

## Scaling Considerations

### When to Migrate from SQLite
- More than 1,000 concurrent users
- High write volume (>100 writes/second)
- Need for replication/clustering

### Migration Path
1. Export data from SQLite
2. Set up PostgreSQL/MySQL
3. Import data
4. Update DATABASE_PATH in `.env`
5. Test thoroughly before switching

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/moodmend/issues
- Email: support@moodmend.com
