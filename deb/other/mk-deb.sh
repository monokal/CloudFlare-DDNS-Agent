echo
echo 'Starting DEB build...'
echo

dpkg-deb --verbose --build ../cloudflare-ddns-agent_1.0-1

echo
echo 'Finished DEB build.'
echo
