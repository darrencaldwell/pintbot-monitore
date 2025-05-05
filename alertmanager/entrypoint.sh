#!/bin/sh

# Add debug output
echo "Starting entrypoint script"
echo "Current webhook URL in config:"
grep "webhook_url:" /etc/alertmanager/config.yml

# Replace the placeholder webhook URL with the actual one from environment variable
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
  echo "Replacing webhook URL with: $DISCORD_WEBHOOK_URL"
  sed -i "s|http://example.com/placeholder-webhook|$DISCORD_WEBHOOK_URL|g" /etc/alertmanager/config.yml
  echo "After replacement:"
  grep "webhook_url:" /etc/alertmanager/config.yml
else
  echo "Warning: DISCORD_WEBHOOK_URL environment variable not set. Using placeholder URL."
fi

# Execute the original entrypoint with all arguments
exec /bin/alertmanager "$@"
