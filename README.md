![CloudFlare logo](https://www.cloudflare.com/media/images/brand/logo-guideline-illustrations_background-white.png)
# CloudFlare DDNS Agent
A dynamic DNS agent for the CloudFlare API. Handy for home projects, development environments, or as part of a DNS-based HA/failover solution (more to come soon, think [Serf](https://www.serfdom.io/)). This allows you to use the benefits of CloudFlare (Hosted DNS, Security, Universal SSL, Apps, etc) without the requirement of a single static endpoint or IP.

## Installation

##### Debian / Ubuntu
Simply installing the DEB package (found in the `deb` directory of this repo) as per below will drop everything in to place and add a cron job to run every hour by default, though this can be tweaked in `/etc/cron.d/cloudflare-ddns-agent`. **See "Configuration" below**.
```bash
sudo dpkg -i cloudflare-ddns-agent_<version>.deb
```

##### Alternative / Other Distros
1. Drop `/etc/cloudflare-ddns-agent/agent.py` in place, found in the `deb/cloudflare-ddns-agent_<version>/etc/cloudflare-ddns-agent` directory of this repo.
2. Drop in a crontab. The example below runs every hour:
```bash
0 * * * * /etc/cloudflare-ddns-agent/agent.py --config /etc/cloudflare-ddns-agent/config.yaml
```
**See "Configuration" below**.

## Configuration
If you installed using the DEB package, the config file can be found at `/etc/cloudflare-ddns-agent/config.yaml`, please edit it as commented in the file.
```bash
vim /etc/cloudflare-ddns-agent/agent.conf
```

If you installed manually, you should copy the example config file found at `/etc/cloudflare-ddns-agent/config.yaml.example` to `/etc/cloudflare-ddns-agent/config.yaml` as shown below and edit it as commented in the file.

```bash
cp /etc/cloudflare-ddns-agent/config.yaml.example /etc/cloudflare-ddns-agent/config.yaml
```
```bash
vim /etc/cloudflare-ddns-agent/agent.conf
```

Should you wish to move the config file, you can tweak the `--config` argument in the cron job seen above.

## Logs
By default, the script will log to `syslog`. In Debian/Ubuntu-based distributions for example, you can follow the logs as per below.
```bash
tail -f /var/log/syslog
```

## Contribute
As always, I welcome any contributions. Just open a **Pull Request**.
