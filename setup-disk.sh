#!/bin/bash
set -e

echo "================================================"
echo "GIS Carbon AI - New Disk Setup Script"
echo "================================================"
echo ""
echo "This script will:"
echo "  1. Format /dev/sda with ext4 filesystem"
echo "  2. Mount it to /mnt/docker-data"
echo "  3. Configure auto-mount in /etc/fstab"
echo "  4. Create directory structure for containers"
echo ""
echo "⚠️  WARNING: This will ERASE all data on /dev/sda!"
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Check if /dev/sda exists
if [ ! -b /dev/sda ]; then
    echo "❌ Error: /dev/sda not found!"
    exit 1
fi

echo ""
echo "Step 1: Formatting /dev/sda with ext4..."
sudo mkfs.ext4 -L docker-data /dev/sda

echo ""
echo "Step 2: Creating mount point..."
sudo mkdir -p /mnt/docker-data

echo ""
echo "Step 3: Mounting the disk..."
sudo mount /dev/sda /mnt/docker-data

echo ""
echo "Step 4: Getting UUID for /etc/fstab..."
UUID=$(sudo blkid -s UUID -o value /dev/sda)
echo "UUID: $UUID"

echo ""
echo "Step 5: Adding entry to /etc/fstab..."
# Check if entry already exists
if grep -q "$UUID" /etc/fstab; then
    echo "Entry already exists in /etc/fstab, skipping..."
else
    echo "UUID=$UUID /mnt/docker-data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
    echo "✅ Added to /etc/fstab"
fi

echo ""
echo "Step 6: Creating directory structure for containers..."
sudo mkdir -p /mnt/docker-data/{postgres,redis,django,geoserver,mapstore,fastapi,jupyter}

# Create subdirectories for specific use cases
sudo mkdir -p /mnt/docker-data/geoserver/gwc  # GeoWebCache tiles
sudo mkdir -p /mnt/docker-data/fastapi/tiles  # GEE tiles cache
sudo mkdir -p /mnt/docker-data/jupyter/datasets  # Large datasets
sudo mkdir -p /mnt/docker-data/jupyter/outputs  # Processing outputs

echo ""
echo "Step 7: Setting permissions..."
sudo chmod -R 755 /mnt/docker-data

# Give ownership to the current user for easier access
sudo chown -R $USER:$USER /mnt/docker-data

echo ""
echo "✅ Setup complete!"
echo ""
echo "Disk information:"
df -h /mnt/docker-data
echo ""
echo "Directory structure:"
tree -L 2 /mnt/docker-data 2>/dev/null || find /mnt/docker-data -maxdepth 2 -type d
echo ""
echo "================================================"
echo "Next steps:"
echo "  1. Review the updated docker-compose.dev.yml"
echo "  2. Restart your containers: docker-compose -f docker-compose.dev.yml down && docker-compose -f docker-compose.dev.yml up -d"
echo "  3. The new disk will be accessible inside containers at /mnt/data"
echo "================================================"

