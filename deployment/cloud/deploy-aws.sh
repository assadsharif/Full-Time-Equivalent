#!/bin/bash
# Personal AI Employee - AWS EC2 Deployment Script
# Platinum Tier - 24/7 Cloud Operation

set -e

echo "🚀 Personal AI Employee - AWS EC2 Deployment"
echo "============================================"
echo ""

# Configuration
INSTANCE_NAME="fte-employee"
INSTANCE_TYPE="t3.medium"  # 2 vCPUs, 4GB RAM (~$30/month)
REGION="us-east-1"
AMI_ID="ami-0c55b159cbfafe1f0"  # Ubuntu 20.04 LTS (update for your region)
KEY_NAME="fte-key"
SECURITY_GROUP="fte-security-group"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Installing..."
    echo ""
    echo "Please install AWS CLI:"
    echo "  macOS:   brew install awscli"
    echo "  Linux:   pip install awscli"
    echo "  Windows: Download from https://aws.amazon.com/cli/"
    echo ""
    echo "Then configure: aws configure"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"
echo ""

# Create SSH key pair
echo "📋 Step 1: SSH Key Setup"
echo "------------------------"
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
    echo "Creating SSH key pair..."
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --region $REGION \
        --query 'KeyMaterial' \
        --output text > ~/.ssh/${KEY_NAME}.pem
    chmod 400 ~/.ssh/${KEY_NAME}.pem
    echo "✅ Key pair created: ~/.ssh/${KEY_NAME}.pem"
else
    echo "✅ Key pair already exists"
fi
echo ""

# Create Security Group
echo "📋 Step 2: Security Group Setup"
echo "--------------------------------"
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)

if ! aws ec2 describe-security-groups --group-names $SECURITY_GROUP --region $REGION &> /dev/null 2>&1; then
    echo "Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP \
        --description "Security group for FTE Employee" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)

    # Allow SSH
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    # Allow HTTP (Dashboard)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 5000 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    echo "✅ Security group created: $SG_ID"
else
    SG_ID=$(aws ec2 describe-security-groups --group-names $SECURITY_GROUP --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
    echo "✅ Security group exists: $SG_ID"
fi
echo ""

# Launch EC2 Instance
echo "📋 Step 3: Launching EC2 Instance"
echo "----------------------------------"
echo "Name:   $INSTANCE_NAME"
echo "Type:   $INSTANCE_TYPE (2 vCPUs, 4GB RAM)"
echo "Region: $REGION"
echo ""

# Check if instance already running
INSTANCE_ID=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null)

if [ "$INSTANCE_ID" != "None" ] && [ -n "$INSTANCE_ID" ]; then
    echo "⚠️  Instance already running: $INSTANCE_ID"
else
    echo "Launching new instance..."

    # User data script for instance initialization
    cat > /tmp/user_data.sh << 'EOFUSERDATA'
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
EOFUSERDATA

    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $SG_ID \
        --region $REGION \
        --user-data file:///tmp/user_data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
        --query 'Instances[0].InstanceId' \
        --output text)

    echo "✅ Instance launched: $INSTANCE_ID"
    echo "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
fi

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "✅ Instance IP: $INSTANCE_IP"
echo ""
echo "Waiting for SSH to be available..."
sleep 45

# Deploy application
echo ""
echo "📋 Step 4: Deploying Application"
echo "---------------------------------"

# Create deployment script
cat > /tmp/deploy_to_ec2.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "Deploying Personal AI Employee..."

# Clone repository
cd /home/ubuntu
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
EOFSCRIPT

# Copy and execute
scp -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no /tmp/deploy_to_ec2.sh ubuntu@$INSTANCE_IP:/tmp/
ssh -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "bash /tmp/deploy_to_ec2.sh"

echo ""
echo "=================================================="
echo "✅ AWS DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "🌐 Your Personal AI Employee is now running 24/7 on AWS!"
echo ""
echo "📊 Dashboard URL:  http://$INSTANCE_IP:5000"
echo "🔗 SSH Access:     ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$INSTANCE_IP"
echo "🆔 Instance ID:    $INSTANCE_ID"
echo ""
echo "💡 Management Commands:"
echo "  View logs:    ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$INSTANCE_IP 'cd fte-employee && sudo docker-compose logs -f'"
echo "  Stop:         ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$INSTANCE_IP 'cd fte-employee && sudo docker-compose down'"
echo "  Restart:      ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$INSTANCE_IP 'cd fte-employee && sudo docker-compose restart'"
echo ""
echo "💰 Cost: ~$30/month (t3.medium instance)"
echo ""
echo "🎉 Platinum Tier Achieved!"
