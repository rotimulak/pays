#!/bin/bash
# Deploy trial tariff feature to production

set -e

echo "=== Deploying Trial Tariff Feature to Production ==="

# 1. SSH to production and run migrations
echo ""
echo "Step 1: Running database migrations..."
ssh root@hhhelper.arsenal0.space << 'ENDSSH'
cd /opt/hhhelper/backend
source venv/bin/activate
alembic upgrade head
ENDSSH

echo "✓ Migrations completed"

# 2. Create trial tariff and promo codes
echo ""
echo "Step 2: Creating trial tariff and promo codes..."
ssh root@hhhelper.arsenal0.space << 'ENDSSH'
cd /opt/hhhelper/backend
source venv/bin/activate
python create_trial_tariff.py
ENDSSH

echo "✓ Trial tariff and promo codes created"

# 3. Restart bot
echo ""
echo "Step 3: Restarting bot..."
ssh root@hhhelper.arsenal0.space << 'ENDSSH'
cd /opt/hhhelper/backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart bot
ENDSSH

echo "✓ Bot restarted"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Test the feature:"
echo "1. Open bot and go to /balance"
echo "2. Click 'Промокод' button"
echo "3. Enter: FRIENDLY"
echo "4. Verify: 30 tokens added, subscription active for 8 days"
