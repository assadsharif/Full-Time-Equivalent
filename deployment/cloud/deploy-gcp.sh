#!/bin/bash
# Personal AI Employee - GCP Compute Engine Deployment
# Platinum Tier - 24/7 Cloud Operation

set -e

echo "🚀 Personal AI Employee - GCP Deployment"
echo "========================================"
echo ""

# Configuration
INSTANCE_NAME="fte-employee"
MACHINE_TYPE="e2-medium"  # 2 vCPUs, 4GB RAM (~$35/month, but FREE with $300 credit)
ZONE="us-central1-a"
IMAGE_FAMILY="debian-11"
IMAGE_PROJECT="debian-cloud"
DISK_SIZE="30GB"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo "✅ Using project: $PROJECT_ID"
echo ""

# Check if instance already exists
EXISTING=$(gcloud compute instances list --filter="name=$INSTANCE_NAME" --format="value(name)" 2>/dev/null || echo "")

if [ -n "$EXISTING" ]; then
    echo "⚠️  Instance '$INSTANCE_NAME' already exists!"
    INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)
    echo "IP Address: $INSTANCE_IP"
    echo ""
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting existing instance..."
        gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --quiet
    else
        echo "Using existing instance..."
        echo "Dashboard URL: http://$INSTANCE_IP:5000"
        exit 0
    fi
fi

# Create firewall rule for dashboard
echo "📋 Step 1: Creating Firewall Rules"
echo "----------------------------------"
if ! gcloud compute firewall-rules describe allow-fte-dashboard &>/dev/null; then
    gcloud compute firewall-rules create allow-fte-dashboard \
        --allow tcp:5000 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow access to FTE Dashboard"
    echo "✅ Firewall rule created"
else
    echo "✅ Firewall rule already exists"
fi
echo ""

# Create instance
echo "📋 Step 2: Creating Compute Engine Instance"
echo "-------------------------------------------"
echo "Name:   $INSTANCE_NAME"
echo "Type:   $MACHINE_TYPE (2 vCPUs, 4GB RAM)"
echo "Zone:   $ZONE"
echo "Disk:   $DISK_SIZE"
echo ""

# Startup script
STARTUP_SCRIPT=$(cat <<'EOFSTARTUP'
#!/bin/bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install git
apt-get update
apt-get install -y git

echo "✅ Server initialization complete"
EOFSTARTUP
)

gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --boot-disk-size=$DISK_SIZE \
    --metadata=startup-script="$STARTUP_SCRIPT" \
    --tags=fte-dashboard

echo "✅ Instance created!"
echo ""

# Wait for instance to be ready
echo "Waiting for instance to be ready..."
sleep 30

# Get instance IP
INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
echo "✅ Instance IP: $INSTANCE_IP"
echo ""

# Wait for SSH to be available
echo "Waiting for SSH to be available..."
for i in {1..12}; do
    if gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="echo 'SSH ready'" &>/dev/null; then
        echo "✅ SSH is ready"
        break
    fi
    echo "Waiting... ($i/12)"
    sleep 10
done
echo ""

# Deploy application
echo "📋 Step 3: Deploying Application"
echo "--------------------------------"

# Create deployment script
DEPLOY_SCRIPT=$(cat <<'EOFDEPLOY'
#!/bin/bash
set -e

echo "Deploying Personal AI Employee..."

# Clone repository
cd /home/$USER
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

# Start services
sudo docker-compose down || true
sudo docker-compose up -d

echo "✅ Services started!"
sudo docker-compose ps
EOFDEPLOY
)

echo "Copying deployment script to instance..."
echo "$DEPLOY_SCRIPT" | gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="cat > /tmp/deploy.sh && chmod +x /tmp/deploy.sh"

echo "Executing deployment..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="bash /tmp/deploy.sh"

echo ""
echo "=================================================="
echo "✅ GCP DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "🌐 Your Personal AI Employee is now running 24/7 on Google Cloud!"
echo ""
echo "📊 Dashboard URL:  http://$INSTANCE_IP:5000"
echo "🔗 SSH Access:     gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "💡 Management Commands:"
echo "  View logs:    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd fte-employee && sudo docker-compose logs -f'"
echo "  Stop:         gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd fte-employee && sudo docker-compose down'"
echo "  Restart:      gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd fte-employee && sudo docker-compose restart'"
echo ""
echo "💰 Cost: ~$35/month (FREE with $300 credit for first 90 days)"
echo ""
echo "🎉 Platinum Tier Achieved!"
