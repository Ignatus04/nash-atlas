#!/bin/bash
# nightly database copy, kept for 14 days (run by /etc/cron.d/atlas-backup)
set -e
D=/opt/atlas/backups
docker exec supabase-db pg_dump -U supabase_admin -d postgres -Fc > $D/db-$(date +%F).dump.tmp && mv $D/db-$(date +%F).dump.tmp $D/db-$(date +%F).dump
find $D -name 'db-*.dump' -mtime +14 -delete
echo "$(date -Is) ok $(du -h $D/db-$(date +%F).dump | cut -f1)"
