# CloudFlare DDNS Agent

A simple dynamic DNS agent written in Python for the CloudFlare API. Handy for home projects or development environments where you want the benefits of CloudFlare (Hosted DNS, Security, Universal SSL, Apps, etc) but don't have a static IP.

#### Usage
Just edit the "CloudFlare config" section at the top of the script, throw it in Cron as per the below example, job's a good 'un.

######Example Cron job (every hour):
```bash
0 * * * * /<absolute-path-to-script>/cloudflare-ddns-agent.py
```
######Default config:
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

#### Logs
By default, the script will log to syslog.

#### Contribute
As always, I welcome any contributions. Just open a Pull Request.
