#!/bin/bash
# Personal AI Employee - DigitalOcean Deployment Script
# Platinum Tier - 24/7 Cloud Operation

set -e

echo "🚀 Personal AI Employee - DigitalOcean Deployment"
echo "=================================================="
echo ""

# Configuration
DROPLET_NAME="fte-employee"
DROPLET_SIZE="s-2vcpu-4gb"  # $24/month
DROPLET_REGION="nyc1"
DROPLET_IMAGE="docker-20-04"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Installing..."
    echo ""
    echo "Please install doctl:"
    echo "  macOS:   brew install doctl"
    echo "  Linux:   snap install doctl"
    echo "  Windows: Download from https://github.com/digitalocean/doctl/releases"
    echo ""
    echo "Then authenticate: doctl auth init"
    exit 1
fi

# Check authentication
if ! doctl account get &> /dev/null; then
    echo "❌ Not authenticated with DigitalOcean"
    echo "Run: doctl auth init"
    exit 1
fi

echo "✅ DigitalOcean CLI configured"
echo ""

# Create SSH key if needed
echo "📋 Step 1: SSH Key Setup"
echo "------------------------"
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "Generating SSH key..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
fi

# Upload SSH key to DigitalOcean
SSH_KEY_NAME="fte-deploy-key"
if ! doctl compute ssh-key list | grep -q "$SSH_KEY_NAME"; then
    echo "Uploading SSH key to DigitalOcean..."
    doctl compute ssh-key import $SSH_KEY_NAME --public-key-file ~/.ssh/id_rsa.pub
fi

SSH_KEY_ID=$(doctl compute ssh-key list --format ID,Name --no-header | grep "$SSH_KEY_NAME" | awk '{print $1}')
echo "✅ SSH Key ID: $SSH_KEY_ID"
echo ""

# Create Droplet
echo "📋 Step 2: Creating Droplet"
echo "----------------------------"
echo "Name:   $DROPLET_NAME"
echo "Size:   $DROPLET_SIZE (2 vCPUs, 4GB RAM)"
echo "Region: $DROPLET_REGION"
echo "Image:  $DROPLET_IMAGE (Ubuntu 20.04 with Docker)"
echo ""

# Check if droplet already exists
if doctl compute droplet list --format Name --no-header | grep -q "^${DROPLET_NAME}$"; then
    echo "⚠️  Droplet already exists!"
    DROPLET_IP=$(doctl compute droplet list --format Name,PublicIPv4 --no-header | grep "^${DROPLET_NAME}" | awk '{print $2}')
    echo "IP Address: $DROPLET_IP"
else
    echo "Creating droplet..."
    doctl compute droplet create $DROPLET_NAME \
        --size $DROPLET_SIZE \
        --image $DROPLET_IMAGE \
        --region $DROPLET_REGION \
        --ssh-keys $SSH_KEY_ID \
        --wait

    DROPLET_IP=$(doctl compute droplet list --format Name,PublicIPv4 --no-header | grep "^${DROPLET_NAME}" | awk '{print $2}')
    echo "✅ Droplet created!"
    echo "IP Address: $DROPLET_IP"
fi

echo ""
echo "Waiting for droplet to be ready..."
sleep 30

# Deploy application
echo ""
echo "📋 Step 3: Deploying Application"
echo "---------------------------------"

# Create deployment script
cat > /tmp/deploy_script.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "Setting up Personal AI Employee on server..."

# Update system
apt-get update
apt-get install -y git curl

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Clone repository
cd /opt
if [ -d "fte-employee" ]; then
    cd fte-employee
    git pull
else
    git clone https://github.com/assadsharif/Personal-AI-Employee-Hackathon-0.git fte-employee
    cd fte-employee
fi

# Create environment file
cat > .env << 'EOF'
VAULT_DIR=/vault
FLASK_ENV=production
ORCHESTRATOR_INTERVAL=300
EOF

# Start services with Docker Compose
docker-compose down || true
docker-compose up -d

echo "✅ Deployment complete!"
echo ""
echo "Services:"
docker-compose ps
EOFSCRIPT

# Copy and execute deployment script
echo "Copying deployment script to server..."
scp -o StrictHostKeyChecking=no /tmp/deploy_script.sh root@$DROPLET_IP:/tmp/

echo "Executing deployment on server..."
ssh -o StrictHostKeyChecking=no root@$DROPLET_IP "bash /tmp/deploy_script.sh"

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "🌐 Your Personal AI Employee is now running 24/7 in the cloud!"
echo ""
echo "📊 Dashboard URL:  http://$DROPLET_IP:5000"
echo "🔗 SSH Access:     ssh root@$DROPLET_IP"
echo ""
echo "💡 Management Commands:"
echo "  View logs:    ssh root@$DROPLET_IP 'cd /opt/fte-employee && docker-compose logs -f'"
echo "  Stop:         ssh root@$DROPLET_IP 'cd /opt/fte-employee && docker-compose down'"
echo "  Restart:      ssh root@$DROPLET_IP 'cd /opt/fte-employee && docker-compose restart'"
echo "  Status:       ssh root@$DROPLET_IP 'cd /opt/fte-employee && docker-compose ps'"
echo ""
echo "💰 Cost: ~$24/month (s-2vcpu-4gb droplet)"
echo ""
echo "🎉 Platinum Tier Achieved!"
