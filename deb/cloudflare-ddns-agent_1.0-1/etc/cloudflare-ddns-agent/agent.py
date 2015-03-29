#!/usr/bin/env python

# Name:          CloudFlare DDNS Agent
# Author:        Daniel Middleton <me@daniel-middleton.com>
# Source:        https://github.com/daniel-middleton/CloudFlare-DDNS-Agent
# Description:   Dynamic DNS agent for the CloudFlare API

# Global imports.
import sys
import requests
import json
import logging
import socket
import ConfigParser

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
def loadIpLog(wanIp):
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

# Description: Load values from config file.
def loadConfig():
    # Absolute path to agent.conf
    configPath = 'agent.conf'

    try:
        # Initialise a ConfigReader and read in agent.conf
        config = ConfigParser.ConfigParser()
        config.read(configPath)
       
        # Read Authentication section
        logging.info('Checking Authentication config...')
        # Email
        email  =   config.get('Authentication', 'Email')
        logging.info("Loaded config (Email)              : %s" % email)

        # API key
        apiKey  =   config.get('Authentication', 'ApiKey')
        logging.info("Loaded config (API key)            : %s" % apiKey)
        # Zone
        zone    =   config.get('Authentication', 'Zone')
        logging.info("Loaded config (Zone)               : %s" % zone)

        # Read General section
        
        # Update Zone?
        logging.info('Loading General config...')
        updateZone = config.get('General', 'UpdateZone')
        logging.info("Loaded config (Update Zone?)       : %s" % updateZone)

        # Read Endpoints section
        
        # CloudFlare API URL
        logging.info('Loading Endpoints config...')
        cfApiUrl = config.get('Endpoints', 'CfApiUrl')
        logging.info("Loaded config (CloudFlare API URL) : %s" % cfApiUrl)
        # IP resolver
        ipResolver = config.get('Endpoints', 'IpResolver')
        logging.info("Loaded config (IP Resolver URL)    : %s" % ipResolver)
        
        # Read Logs section
        
        # Run log location
        logging.info('Loading Logs config...')
        runLog = config.get('Logs', 'RunLog')
        logging.info("Loaded config (Run log location)   : %s" % runLog)
        # IP log location
        ipLog = config.get('Logs', 'IpLog')
        logging.info("Loaded config (IP log location)    : %s" % ipLog)

        return config._sections

    except KeyError:
        logging.error("Missing key in config (%s). Exiting." % configPath)

    except:
        logging.error("Error while parsing config (%s). Exiting." % configPath)

    sys.exit(1)

# Description: Orchestrate the whole operation.
def main():
#    try:
        # First, load in values from the config file.
        config = loadConfig()

        
        # Then get our current WAN IP.
        #wanIp = getWanIp()

        # Then check if that IP has changed since the last run.
        #loadIpLog(wanIp)

        # If it has, get all existing DNS records from CloudFlare.
        #records = getRecords()

        # Then for each of our records.
        #for name in names:
            # Get the record ID.
        #    recordId = getRecordId(name)

            # And update the it with our new IP.
        #    updateRecord(name, recordId)
    
#    except:
#        logging.error('Something bad happened in main. Exiting.')
    

# Execute script
logging.info('DDNS update started...')

# Orchestrate the whole operation.
main()

# Exit
logging.info('DDNS update completed.')
sys.exit(0)
