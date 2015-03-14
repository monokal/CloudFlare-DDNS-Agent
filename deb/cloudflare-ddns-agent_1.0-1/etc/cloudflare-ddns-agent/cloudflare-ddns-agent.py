#!/usr/bin/env python

###############################################################################
# Name:          CloudFlare DDNS Agent
# Author:        Daniel Middleton <me@daniel-middleton.com>
# Description:   Dynamic DNS agent for the CloudFlare API
# Prerequisites: Python (tested 2.7.6)
# Usage:         Cron: "0 * * * * /path-to-script/cloudflare-ddns-agent.py"
###############################################################################

# Imports
import sys
import requests
import json
import logging
import logging.handlers

############################ CloudFlare config ################################

# The Email address used to login to CloudFlare.
EMAIL   = 'YOUR-NAME@YOUR-DOMAIN.TLD'

# Your CloudFlare API key which can be found at https://www.cloudflare.com/my-account.html
API_KEY = 'YOUR-API-KEY'

# The Zone (website) name to update.
ZONE    = 'YOUR-ZONE.TLD'

# Names of A records to update.
names = []
names.append(ZONE) # Root domain
names.append('www')
#names.append('<Another A record>')

############################## End of config ##################################

# Other globals
IP_RESOLVER = 'http://icanhazip.com'
PROG_NAME   = 'CloudFlare DDNS Agent'
API_URL     = 'https://www.cloudflare.com/api_json.html'
IP_LOG      = '/tmp/cf_ddns_iplog.txt'

# Logging config
ddns_log = logging.getLogger('DdnsLog')
ddns_log.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
ddns_log.addHandler(handler)

# Desc: Returns WAN IP of the host
def getWanIp():
    ddns_log.debug('Resolving WAN IP...')

    try:
        response = requests.get(IP_RESOLVER)
        if response.status_code <> 200:
            ddns_log.debug('Error obtaining WAN IP - 1.')
            sys.exit(1)
    except:
        ddns_log.debug('Error obtaining WAN IP - 2.')
        sys.exit(1)
    
    wanIp = response.text.strip()
    response.close()

    ddns_log.debug("WAN IP resolved as: %s." % wanIp)
    return wanIp

# Desc: Get all existing records from CloudFlare
def getRecords():
    ddns_log.debug('Obtaining records from CloudFlare API...')

    # Define API payload
    payload = {
        'a'     : 'rec_load_all',
        'tkn'   : API_KEY,
        'email' : EMAIL,
        'z'     : ZONE, 
    }

    # Get all records via API and parse to JSON
    try:
        response = requests.get(API_URL, params=payload)
        if response.status_code <> 200:
            ddns_log.debug('Error obtaining records from CloudFlare API - 1.')
            sys.exit(1)
    except:
        ddns_log.debug('Error obtaining records from CloudFlare API - 2.')
        sys.exit(1)
    
    records = response.json()
    response.close()
    
    ddns_log.debug('obtained records from cloudflare api.')
    return records

# Desc: Get ID of a given record name
def getRecordId(name):
    ddns_log.debug("Obtaining record ID for: %s" % name)

    # For given name return record ID
    for record in records['response']['recs']['objs']:
        if record['display_name'] == name:
            ddns_log.debug("Obtained record ID: %s" % record['rec_id'])
            return record['rec_id']
        
    ddns_log.debug("Could not obtain record ID for: %s" % name)
    sys.exit(1)

# Desc: Update given record with new WAN IP
def updateRecord(name,recordId):
    ddns_log.debug("Updating record '%s' to point at '%s'..." % (name,wanIp))
    
    # Define payload
    payload = {
        'a'            : 'rec_edit',
        'tkn'          : API_KEY,
        'email'        : EMAIL,
        'z'            : ZONE,
        'type'         : 'A',
        'id'           : recordId,
        'name'         : name,
        'content'      : wanIp,
        'ttl'          : 1,
        'service_mode' : 1,
    }
    try:
        # Update the record
        response = requests.get(API_URL, params=payload)
        if response.status_code <> 200:
            ddns_log.debug('Error updating record via CloudFlare API - 1.')
            sys.exit(1)
    except:
        ddns_log.debug('Error updating record via CloudFlare API - 2.')
        sys.exit(1)

    ddns_log.debug('Updated record successfully.')

def checkIpLog():
    try:
        # Open log or create if doesn't exist
        file = open(IP_LOG, 'a+')
        try:
            ddns_log.debug('Found IP log. Persing data...')
            file.seek(0)
            ipLog = json.load(file)
            ddns_log.debug('Parsed IP log.')
        except ValueError:
            ddns_log.debug('Could not parse IP log.')
            ipLog = {}
        file.close()
    except IOError:
        ddns_log.debug('Could not access IP log. Exiting.')
        sys.exit(1)

# Execute script
ddns_log.debug("%s started..." % PROG_NAME)

# Get WAN IP
wanIp = getWanIp()

# Check if IP has changed since last run
#checkIpLog()

# Get all records from CloudFlare
records = getRecords()

# For each name update the record
for name in names:
    recordId = getRecordId(name)
    updateRecord(name,recordId)

# Exit
ddns_log.debug("%s completed." % PROG_NAME)
sys.exit(0)
