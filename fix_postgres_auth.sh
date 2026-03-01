#!/bin/bash
# ============================================================================
# Fix PostgreSQL Authentication
# ============================================================================

echo "🔧 Fixing PostgreSQL Authentication..."

# Find pg_hba.conf location
PG_HBA=$(sudo -u postgres psql -t -P format=unaligned -c 'SHOW hba_file;')
echo "📁 pg_hba.conf location: $PG_HBA"

# Backup original file
echo "💾 Creating backup..."
sudo cp "$PG_HBA" "${PG_HBA}.backup.$(date +%Y%m%d_%H%M%S)"

# Update authentication method from 'peer' to 'md5'
echo "🔄 Updating authentication method..."
sudo sed -i 's/local   all             postgres                                peer/local   all             postgres                                md5/' "$PG_HBA"
sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/' "$PG_HBA"

# Show changes
echo ""
echo "📋 Updated configuration:"
sudo grep -E "^local.*all.*all" "$PG_HBA"

# Reload PostgreSQL
echo ""
echo "🔄 Reloading PostgreSQL..."
sudo systemctl reload postgresql

echo ""
echo "✅ Authentication fixed!"
echo ""
echo "Now run: bash setup_database.sh"
