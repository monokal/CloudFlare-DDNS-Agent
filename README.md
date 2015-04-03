# CloudFlare DDNS Agent
A dynamic DNS agent for the CloudFlare API. Handy for home projects, development environments, or as part of a DNS-based HA/failover solution where you want the benefits of CloudFlare (Hosted DNS, Security, Universal SSL, Apps, etc) but don't have a single endpoint or static IP.

## Installation

##### Debian / Ubuntu
Simply installing the DEB package (found in "deb" folder of this repo) as per below will drop everything in to place and add a cron job to run every hour by default, though this can be tweaked in "/etc/cron.d/cloudflare-ddns-agent". See "Configuration" below.
```bash
sudo dpkg -i cloudflare-ddns-agent_<version>.deb
```

##### Alternative / Other Distros
- Drop "/etc/cloudflare-ddns-agent/agent.py" in place, found in the "deb/cloudflare-ddns-agent_<version>/etc/cloudflare-ddns-agent" directory of this repo.
- Drop in a crontab. The example below runs every hour:
```bash
0 * * * * /etc/cloudflare-ddns-agent/agent.py --config /etc/cloudflare-ddns-agent/agent.conf
```
- See "Configuration" below.

## Configuration
By default, an "agent.conf" file is expected to be found at "/etc/cloudflare-ddns-agent/agent.conf", although you can tweak the "--config" argument in the cron job. You should copy the example config file found at "/etc/cloudflare-ddns-agent/agent.conf.example" as per below, and edit it as commented.

```bash
cp /etc/cloudflare-ddns-agent/agent.conf.example /etc/cloudflare-ddns-agent/agent.conf
```
```bash
vim /etc/cloudflare-ddns-agent/agent.conf
```

## Usage
text

## Logs
By default, the script will log to syslog.

## Contribute
As always, I welcome any contributions. Just open a Pull Request.
