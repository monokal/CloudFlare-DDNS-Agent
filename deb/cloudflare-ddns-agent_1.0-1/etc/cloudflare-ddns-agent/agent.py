#!/usr/bin/env python

# Name:          CloudFlare DDNS Agent
# Author:        Daniel Middleton <me@daniel-middleton.com>
# Description:   Dynamic DNS agent for the CloudFlare API

################################### CONFIG ####################################
# TODO: Break config out in to its own file.
# TODO: Add support for other record types.

# The Email address used to login to CloudFlare.
EMAIL   = 'YOUR-NAME@YOUR-DOMAIN.TLD'

# Your CloudFlare API key which can be found at https://www.cloudflare.com/my-account.html
API_KEY = 'YOUR-API-KEY'

# The Zone (website) name to update.
ZONE    = 'YOUR-ZONE.TLD'

# Names of A records to update
names = []
names.append(ZONE)
names.append('www')
#names.append('<Another A record>')

# Other globals

# There's clearly a potential vulnerability here should the below resolver service be
# compromised. You can change this to point at a self-hosted service if necessary or
# I'll host a secure public resolver for this purpose if requested.
IP_RESOLVER = 'http://icanhazip.com'

API_URL     = 'https://www.cloudflare.com/api_json.html'
IP_LOG      = '/tmp/cf_ddns_iplog.txt'

############################ No need to edit below ############################

# Global imports.
import sys
import requests
import json
import logging
import socket

# Global vars.
PROG_NAME = 'CloudFlare DDNS Agent'

# Logging config.
logging.basicConfig(
    format=PROG_NAME+' : %(levelname)s : %(message)s',
    filename='/var/log/cloudflare-ddns-agent.log',
    level=logging.INFO
)

# Description: Check a generic HTTP status code.
def checkHttpResponse(code):
    try:
        # If HTTP status is OK then return immediately.
        if code == 200:
            logging.info('200 - OK.')
            return
        # Otherwise, log appropriate error and exit.
        elif code == 400:
            logging.error('400 - Bad Request. Exiting.')
        elif code == 401:
            logging.error('401 - Unauthorised. Exiting.')
        elif code == 403:
            logging.error('403 - Forbidden. Exiting.')
        elif code == 404:
            logging.error('404 - Not Found. Exiting.')
        elif code == 410:
            logging.error('410 - Gone. Exiting.')
        elif code == 500:
            logging.error('500 - Internal Server Error. Exiting.')
        elif code == 501:
            logging.error('501 - Not Implemented. Exiting.')
        elif code == 503:
            logging.error('503 - Service Unavailable. Exiting.')
        elif code == 550:
            logging.error('550 - Permission Denied. Exiting.')
        else:
            logging.error("%i - Unrecognised HTTP return code. Exiting." % code)

    except:
            logging.error('Error parsing HTTP return code. Exiting.')
        
    sys.exit(1)

# Description: Check a CloudFlare API HTTP response.
def checkApiResponse(response):
    # If HTTP status code isn't OK, log error and exit immediately.
    checkHttpResponse(response.status_code)

    # Otherwise, parse response body to JSON.
    try:
        responseJson = json.load(response.text)

    except:
        logging.error('Error parsing HTTP response body to JSON. Exiting.')
        sys.exit(1)

    try:
        # If result is success, return immediately.
        if responseJson["result"] == 'success':
            logging.info('Result: Success.')
            return

        # Otherwise, log appropriate error and exit.
        elif responseJson["result"] == 'E_UNAUTH':
            logging.info('Result: E_UNAUTH - Authentication could not be completed. Exiting.')
        
        elif responseJson["result"] == 'E_INVLDINPUT':
            logging.info('Result: E_INVLDINPUT - Some other input was not valid. Exiting.')
        
        elif responseJson["result"] == 'E_MAXAPI':
            logging.info('Result: E_MAXAPI - You have exceeded your allowed number of API calls. Exiting.')
        
        else:
            logging.info("Result: %s - Unrecognised API result. Exiting." % responseJson["result"])

    except:
        logging.error('Error analysing the JSON response body. Exiting.')

    sys.exit(1)

# Description: Returns WAN IP of the host.
def getWanIp():
    logging.info('Resolving WAN IP...')

    try:
        # Attempt GET request to resolver.
        response = requests.get(IP_RESOLVER)

        # If HTTP status code isn't OK, log error and exit immediately.
        checkHttpResponse(response.status_code)

    except:
        logging.error("Error obtaining WAN IP from '%s'." % IP_RESOLVER)
        sys.exit(1)

    try:
        # Otherwise, try to extract the IP.
        wanIp = response.text.strip()
        response.close()
        
        # Throw an exception if the IP is invalid.
        socket.inet_aton(wanIp)

        # If we've made it this far we can happily return our WAN IP.
        logging.info("WAN IP resolved as: %s" % wanIp)
        return wanIp

    except socket.error:
        logging.error("Invalid WAN IP obtained from '%s'." % IP_RESOLVER)
    
    except:
        logging.error("Error validating WAN IP from '%s'." % IP_RESOLVER)
    
    sys.exit(1)

# Description: Get all of our existing DNS records from CloudFlare API.
def getRecords():
    logging.info('Obtaining existing DNS records from CloudFlare API...')

    # Construct payload.
    payload = {
        'a'     : 'rec_load_all',
        'tkn'   : API_KEY,
        'email' : EMAIL,
        'z'     : ZONE, 
    }

    try:
        # Perform the GET request.
        response = requests.get(API_URL, params=payload)
        
        # If API response isn't good, log error and exit immediately.
        checkApiResponse(response)
    
    except:
        logging.error('Error obtaining DNS records from CloudFlare API.')
        sys.exit(1)
    
    try:
        recordsJson = json.load(response.text)
        response.close()
    
        logging.info("Obtained %i DNS records from CloudFlare API." % recordsJson["response"]["recs"]["count"])
        return records

    except:
        logging.error('Error parsing records to JSON. Exiting.')
    
    sys.exit(1)

# Description: Return ID of a given record name.
def getRecordId(name):
    logging.info("Searching for record ID of: %s" % name)

    try:
        # Search records for the required name.
        for record in records['response']['recs']['objs']:
            # When found, return its ID.
            if record['display_name'] == name:
                logging.info("Obtained record ID: %s" % record['rec_id'])
                return record['rec_id']
                
        # If we're here, we couldn't find the record name.
        logging.error("Could not find a record matching: %s" % name)
    
    except:
        logging.error('Error while searching for record. Exiting.')

    sys.exit(1)

# Description: Update a given record with new WAN IP.
def updateRecord(name, recordId):
    logging.info("Updating '%s' to point at '%s'..." % (name, wanIp))
    
    # Construct payload.
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
        # Try to update the record.
        response = requests.get(API_URL, params=payload)
        
        # If API response isn't good, log error and exit immediately.
        checkApiResponse(response)
    
        # Otherwise, log success and return.
        logging.info('Record updated successfully.')
        return

    except:
        logging.error('Error updating record via CloudFlare API.')
    
    sys.exit(1)

# Description:
def checkIpLog(wanIp):
    try:
        # Open log or create if doesn't exist
        file = open(IP_LOG, 'a+')
        try:
            logging.info('Found IP log. Parsing data...')
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

# Description: Orchestrate the whole operation.
def main():
    try:
        # First, get our current WAN IP.
        wanIp = getWanIp()

        # Then check if that IP has changed since the last run.
        checkIpLog(wanIp)

        # If it has, get all existing DNS records from CloudFlare.
        records = getRecords()

        # Then for each of our records.
        for name in names:
            # Get the record ID.
            recordId = getRecordId(name)

            # And update the it with our new IP.
            updateRecord(name, recordId)
    
    except:
        logging.error('Something bad happened in main. Exiting.')
    
    sys.exit(1)

# Execute script
logging.info('DDNS update started...')

# Orchestrate the whole operation.
main()

# Exit
logging.info('DDNS update completed.')
sys.exit(0)
