echo 'Removing cloudflare-ddns-agent package...'
sudo dpkg --remove --force-remove-reinstreq cloudflare-ddns-agent
sudo rm -rf /etc/cloudflare-ddns-agent
echo 'Finished.'
