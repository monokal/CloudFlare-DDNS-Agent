#!/usr/bin/env python

# Name:          CloudFlare DDNS Agent
# Author:        Daniel Middleton <me@daniel-middleton.com>
# Description:   Dynamic DNS agent for the CloudFlare API

################################### CONFIG ####################################
# TODO: Break config out in to its own file
# TODO: Add support for other record types

# The Email address used to login to CloudFlare
EMAIL   = 'YOUR-NAME@YOUR-DOMAIN.TLD'

# Your CloudFlare API key which can be found at https://www.cloudflare.com/my-account.html
API_KEY = 'YOUR-API-KEY'

# The Zone (website) name to update
ZONE    = 'YOUR-ZONE.TLD'

# Names of A records to update
names = []
names.append(ZONE)
names.append('www')
#names.append('<Another A record>')

############################ No need to edit below ############################

# Global imports
import sys
import requests
import json
import logging

# Other globals

# There's clearly a potential vulnerability here should the below resolver service be
# compromised. You can change this to point at a self-hosted service if necessary or
# I'll host a secure public resolver for this purpose if requested.
IP_RESOLVER = 'http://icanhazip.com'

API_URL     = 'https://www.cloudflare.com/api_json.html'
IP_LOG      = '/tmp/cf_ddns_iplog.txt'
PROG_NAME   = 'CloudFlare DDNS Agent'

# Logging config
logging.basicConfig(
    format=PROG_NAME+' : %(levelname)s : %(message)s',
    filename='/var/log/cloudflare-ddns-agent.log',
    level=logging.INFO
)

# Desc: Check a generic HTTP response code
def checkHttpResponse(responseCode):
    if responseCode == 200:
        logging.info('200 - OK')
    elif responseCode == 400:
        logging.error('400 - Bad Request. Exiting.')
        sys.exit(1)
    elif responseCode == 401:
        logging.error('401 - Unauthorised. Exiting.')
        sys.exit(1)
    elif responseCode == 403:
        logging.error('403 - Forbidden. Exiting.')
        sys.exit(1)
    elif responseCode == 404:
        logging.error('404 - Not Found. Exiting.')
        sys.exit(1)
    elif responseCode == 410:
        logging.error('410 - Gone. Exiting.')
        sys.exit(1)
    elif responseCode == 500:
        logging.error('500 - Internal Server Error. Exiting.')
        sys.exit(1)
    elif responseCode == 501:
        logging.error('501 - Not Implemented. Exiting.')
        sys.exit(1)
    elif responseCode == 503:
        logging.error('503 - Service Unavailable. Exiting.')
        sys.exit(1)
    elif responseCode == 550:
        logging.error('550 - Permission Denied. Exiting.')
        sys.exit(1)
    else:
        logging.error('Unrecognised HTTP response code returned. Exiting.')
        sys.exit(1)

# Desc: Check the CloudFlare API HTTP response code
def checkApiResponse(responseCode):
    checkHttpResponse(responseCode)
#   TODO: If CloudFlare call, actually check response body and throw approprite error as per below:
#       "E_UNAUTH" -- Authentication could not be completed
#       "E_INVLDINPUT" -- Some other input was not valid
#       "E_MAXAPI" -- You have exceeded your allowed number of API calls.

# Desc: Returns WAN IP of the host
def getWanIp():
    logging.info('Resolving WAN IP...')

    try:
        response = requests.get(IP_RESOLVER)
        checkHttpResponse(response.status_code)
    except:
        logging.error('Error obtaining WAN IP.')
        sys.exit(1)
    
    wanIp = response.text.strip()
    response.close()

    logging.info("WAN IP resolved as: %s." % wanIp)
    return wanIp

# Desc: Get all existing records from CloudFlare
def getRecords():
    logging.info('Obtaining records from CloudFlare API...')

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
        checkApiResponse(response.status_code)
    except:
        logging.error('Error obtaining records from CloudFlare API.')
        sys.exit(1)
    
    records = response.json()
    response.close()
    
    logging.info('obtained records from cloudflare api.')
    return records

# Desc: Get ID of a given record name
def getRecordId(name):
    logging.info("Obtaining record ID for: %s" % name)

    # For given name return record ID
    for record in records['response']['recs']['objs']:
        if record['display_name'] == name:
            logging.info("Obtained record ID: %s" % record['rec_id'])
            return record['rec_id']
        
    logging.error("Could not obtain record ID for: %s" % name)
    sys.exit(1)

# Desc: Update given record with new WAN IP
def updateRecord(name,recordId):
    logging.info("Updating record '%s' to point at '%s'..." % (name,wanIp))
    
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
        checkApiResponse(response.status_code)
    except:
        logging.error('Error updating record via CloudFlare API.')
        sys.exit(1)

    logging.info('Updated record successfully.')

def checkIpLog():
    try:
        # Open log or create if doesn't exist
        file = open(IP_LOG, 'a+')
        try:
            logging.info('Found IP log. Persing data...')
            file.seek(0)
            ipLog = json.load(file)
            logging.info('Parsed IP log.')
        except ValueError:
            logging.error('Could not parse IP log.')
            ipLog = {}
        file.close()
    except IOError:
        logging.error('Could not access IP log. Exiting.')
        sys.exit(1)

# Execute script
logging.info("%s started..." % PROG_NAME)

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
logging.info("%s completed." % PROG_NAME)
sys.exit(0)
