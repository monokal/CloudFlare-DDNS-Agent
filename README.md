# CloudFlare DDNS Agent
A simple dynamic DNS agent written in Python for the CloudFlare API. Handy for home projects or development environments where you want the benefits of CloudFlare (Hosted DNS, Security, Universal SSL, Apps, etc) but don't have a static IP.

## Installation

##### Debian / Ubuntu
Simply installing the DEB package (found in "deb" folder) as per below will drop everything in to place and add a cron job to run every hour by default, though this can be tweaked in "/etc/cron.d/cloudflare-ddns-agent".
```bash
sudo dpkg -i cloudflare-ddns-agent_1.0-1.deb
```

##### Alternative / Other Distros
- Drop "/etc/cloudflare-ddns-agent/cloudflare-ddns-agent.py" in place.
- Drop in a crontab. Example below runs every hour:
```bash
0 * * * * /etc/cloudflare-ddns-agent/cloudflare-ddns-agent.py
```

## Configuration
Just edit the "CloudFlare config" section at the top of the script (/etc/cloudflare-ddns-agent/cloudflare-ddns-agent.py) as seen below:

```python
############################ CloudFlare config ################################

# API credentials
EMAIL           =       'YOUR-NAME@YOUR-DOMAIN.TLD'
API_KEY         =       'YOUR-API-KEY'

# Zone name
ZONE            =       'YOUR-ZONE.TLD'

# Names of A records to update, add more lines as required
names = []
names.append(ZONE) # Root domain
names.append('www')

############################## End of config ##################################
```

## Logs
By default, the script will log to syslog.

## Contribute
As always, I welcome any contributions. Just open a Pull Request.
