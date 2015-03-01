# CloudFlare DDNS Agent

Dynamic DNS agent for the CloudFlare API. Handy for home projects or development environments where you want the benefits of CloudFlare but don't have a static IP.

## Usage
Just edit the "CloudFlare config" section at the top of the script, throw it in Cron as per the below example, job's a good 'un.

E.g. To run every hour, add the following Cron job:
0 * * * * /<absolute-path-to-script>/cloudflare-ddns-agent.py

## Logs
By default, the script will log to syslog.

## Contribute
As always, I welcome any contributions. Just open a Pull Request.
