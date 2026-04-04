#!/bin/bash
set -e

# Setup secrets for Athanor deployment
# This script prompts for sensitive values and creates a local .env file
# The .env file is gitignored and never committed to the repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="$SCRIPT_DIR/infra/envs"
ENV_FILE="$ENV_DIR/.env.prod"

echo "🔐 Athanor Secrets Setup"
echo "========================"
echo ""
echo "This script will prompt for sensitive values and create:"
echo "  $ENV_FILE"
echo ""
echo "⚠️  IMPORTANT: This file is gitignored and should NEVER be committed."
echo ""

# Check if .env.prod already exists
if [ -f "$ENV_FILE" ]; then
    read -p "⚠️  $ENV_FILE already exists. Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Prompt for secrets
echo ""
echo "Enter your secrets. Press Ctrl+C to cancel."
echo ""

read -sp "OpenRouter API Key (sk-or-v1-...): " OPENROUTER_KEY
echo
if [ -z "$OPENROUTER_KEY" ]; then
    echo "❌ OpenRouter API key is required."
    exit 1
fi

read -sp "OpenWebUI Secret Key (for JWT signing): " WEBUI_SECRET
echo
if [ -z "$WEBUI_SECRET" ]; then
    echo "❌ WebUI secret key is required."
    exit 1
fi

# Create .env.prod file
cat > "$ENV_FILE" << EOF
export TF_VAR_openrouter_api_key="$OPENROUTER_KEY"
export TF_VAR_webui_secret_key="$WEBUI_SECRET"
EOF

chmod 600 "$ENV_FILE"

echo ""
echo "✅ Secrets file created at: $ENV_FILE"
echo ""
echo "Next steps:"
echo "1. Source the secrets file:"
echo "   source infra/envs/.env.prod"
echo ""
echo "2. Initialize Terraform (if not already done):"
echo "   gcloud auth login"
echo "   gcloud config set project athanor-ai"
echo "   terraform -chdir=infra init"
echo ""
echo "3. Plan the deployment:"
echo "   terraform -chdir=infra plan -var-file=envs/prod.tfvars"
echo ""
echo "4. Apply the deployment:"
echo "   terraform -chdir=infra apply -var-file=envs/prod.tfvars"
echo ""
