# 🚀 Cloud Deployment Guide - Platinum Tier

**Personal AI Employee - 24/7 Cloud Operation**

---

## 📋 Overview

This guide covers deploying your Personal AI Employee to the cloud for **24/7 operation**. All services run automatically in Docker containers with auto-restart on failure.

### ✅ What Gets Deployed

- 🌐 **Web Dashboard** (Port 5000)
- 📁 **Filesystem Watcher** (Background)
- 🤖 **Orchestrator** - Ralph Wiggum Loop (Background)
- 💾 **Persistent Vault Storage**
- 🔄 **Auto-restart** on failures
- 📊 **Health checks** every 30 seconds

---

## 🌍 Cloud Provider Options

### Option 1: DigitalOcean (Recommended - Simplest)

**Cost:** ~$24/month
**Specs:** 2 vCPUs, 4GB RAM, 80GB SSD
**Region:** Choose nearest to you

**Pros:**
- Simplest setup
- Pre-configured Docker images
- Great documentation
- Affordable pricing

**Deploy:**
```bash
chmod +x deployment/cloud/deploy-digitalocean.sh
./deployment/cloud/deploy-digitalocean.sh
```

**Requirements:**
1. DigitalOcean account
2. Install `doctl` CLI
3. Run `doctl auth init`

---

### Option 2: AWS EC2

**Cost:** ~$30/month
**Specs:** t3.medium (2 vCPUs, 4GB RAM)
**Region:** us-east-1 (configurable)

**Pros:**
- Most powerful/scalable
- Enterprise-grade
- Global presence
- Free tier eligible (12 months)

**Deploy:**
```bash
chmod +x deployment/cloud/deploy-aws.sh
./deployment/cloud/deploy-aws.sh
```

**Requirements:**
1. AWS account
2. Install AWS CLI
3. Run `aws configure`

---

### Option 3: Manual Docker Deployment

**For any cloud provider (GCP, Azure, Linode, etc.)**

```bash
# 1. SSH into your server
ssh your-server

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 4. Clone repository
git clone https://github.com/assadsharif/Personal-AI-Employee-Hackathon-0.git fte-employee
cd fte-employee

# 5. Create environment file
cat > .env << EOF
VAULT_DIR=/vault
FLASK_ENV=production
ORCHESTRATOR_INTERVAL=300
EOF

# 6. Start services
docker-compose up -d

# 7. Check status
docker-compose ps
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Vault location
VAULT_DIR=/vault

# Flask settings
FLASK_ENV=production
FLASK_DEBUG=0

# Orchestrator settings
ORCHESTRATOR_INTERVAL=300  # 5 minutes in seconds

# Watcher settings
WATCH_INTERVAL=30  # seconds

# Optional: API credentials
ANTHROPIC_API_KEY=your_key_here
LINKEDIN_CLIENT_ID=your_id
LINKEDIN_CLIENT_SECRET=your_secret
XERO_CLIENT_ID=your_id
XERO_CLIENT_SECRET=your_secret
```

### Firewall Rules

**Required ports:**
- **5000** - Web Dashboard (HTTP)
- **22** - SSH (for management)

**Optional:**
- **443** - HTTPS (with reverse proxy)
- **80** - HTTP redirect to HTTPS

---

## 🚀 Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] Cloud provider account created
- [ ] CLI tools installed and configured
- [ ] SSH keys generated
- [ ] Repository is public or SSH key added
- [ ] Environment variables prepared

### 2. Run Deployment Script

**DigitalOcean:**
```bash
./deployment/cloud/deploy-digitalocean.sh
```

**AWS:**
```bash
./deployment/cloud/deploy-aws.sh
```

### 3. Verify Deployment

```bash
# Get your server IP from deployment output
SERVER_IP=<your-ip>

# Check dashboard
curl http://$SERVER_IP:5000

# Or open in browser
# http://<your-ip>:5000
```

### 4. Configure DNS (Optional)

Point your domain to the server IP:

```
A Record:  fte.yourdomain.com  →  <server-ip>
```

Then access: `http://fte.yourdomain.com:5000`

---

## 📊 Monitoring & Management

### View Running Services

```bash
ssh root@<server-ip>
cd /opt/fte-employee  # or ~/fte-employee on AWS
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f orchestrator
docker-compose logs -f filesystem-watcher
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart dashboard
```

### Stop Services

```bash
docker-compose down
```

### Start Services

```bash
docker-compose up -d
```

### Update Application

```bash
cd /opt/fte-employee
git pull
docker-compose down
docker-compose up -d --build
```

---

## 🔒 Security Best Practices

### 1. Use HTTPS

Install Nginx reverse proxy with Let's Encrypt:

```bash
# Install Nginx
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

# Configure reverse proxy
cat > /etc/nginx/sites-available/fte << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/fte /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Get SSL certificate
certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration

```bash
# Ubuntu/Debian
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# For internal access only (more secure):
# ufw allow from <your-ip> to any port 5000
```

### 3. Automatic Backups

```bash
# Add to crontab
crontab -e

# Backup vault daily at 2 AM
0 2 * * * docker exec fte-dashboard tar czf /backup/vault-$(date +\%Y\%m\%d).tar.gz /vault
```

### 4. Environment Secrets

Never commit secrets to Git. Use environment files:

```bash
# Create secrets file (not in Git)
cat > /opt/fte-employee/.env.secrets << EOF
ANTHROPIC_API_KEY=sk-ant-...
LINKEDIN_CLIENT_SECRET=...
XERO_CLIENT_SECRET=...
EOF

chmod 600 /opt/fte-employee/.env.secrets
```

---

## 💰 Cost Estimates

### Monthly Costs

| Provider | Instance Type | vCPUs | RAM | Storage | Cost/Month |
|----------|--------------|-------|-----|---------|------------|
| **DigitalOcean** | s-2vcpu-4gb | 2 | 4GB | 80GB | $24 |
| **AWS EC2** | t3.medium | 2 | 4GB | 30GB | $30 |
| **GCP** | e2-medium | 2 | 4GB | 30GB | $35 |
| **Azure** | B2s | 2 | 4GB | 30GB | $37 |
| **Linode** | Linode 4GB | 2 | 4GB | 80GB | $24 |

**Additional costs:**
- Bandwidth: Usually included (1-3TB/month)
- Backups: +$3-5/month
- DNS/Domain: ~$12/year
- SSL: Free (Let's Encrypt)

**Total estimated cost:** $25-40/month

---

## 🔍 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs <service-name>

# Rebuild image
docker-compose up -d --build

# Check disk space
df -h
```

### Dashboard not accessible

```bash
# Check if port 5000 is open
netstat -tlnp | grep 5000

# Check firewall
ufw status

# Check container
docker ps | grep dashboard
```

### Out of memory

```bash
# Check memory usage
free -h

# Upgrade to larger instance or add swap:
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Services keep restarting

```bash
# Check health checks
docker inspect <container-name> | grep -A 10 Health

# Disable health check temporarily
# Remove healthcheck section from docker-compose.yml
```

---

## 📈 Scaling

### Vertical Scaling (More Resources)

**DigitalOcean:**
```bash
# Resize droplet via web UI or CLI
doctl compute droplet-action resize <droplet-id> --size s-4vcpu-8gb
```

**AWS:**
```bash
# Stop instance, change type, restart
aws ec2 stop-instances --instance-ids <id>
aws ec2 modify-instance-attribute --instance-id <id> --instance-type t3.large
aws ec2 start-instances --instance-ids <id>
```

### Horizontal Scaling (Multiple Instances)

Use Docker Swarm or Kubernetes for multi-server setup.

---

## ✅ Post-Deployment Checklist

- [ ] All services running (`docker-compose ps`)
- [ ] Dashboard accessible (`http://<ip>:5000`)
- [ ] Vault data persisting (`docker volume ls`)
- [ ] Logs being written (`docker-compose logs`)
- [ ] Auto-restart working (restart container and check)
- [ ] DNS configured (optional)
- [ ] HTTPS enabled (optional)
- [ ] Backups configured
- [ ] Firewall configured
- [ ] Monitoring set up

---

## 🎉 Success!

Your Personal AI Employee is now running **24/7 in the cloud**!

**Access your dashboard:**
```
http://<your-server-ip>:5000
```

**Platinum Tier Status:** ✅ ACHIEVED

---

## 📞 Support

**Repository:** https://github.com/assadsharif/Personal-AI-Employee-Hackathon-0
**Documentation:** See `docs/` directory
**Issues:** GitHub Issues

---

**Built with:** Claude Sonnet 4.5 + Docker + Python 3.13
**Achievement:** Platinum Tier (Cloud Deployment)
**Status:** Production Ready for 24/7 Operation ✅
