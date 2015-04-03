#!/usr/bin/env python

# Name:          CloudFlare DDNS Agent
# Author:        Daniel Middleton <me@daniel-middleton.com>
# Source:        https://github.com/daniel-middleton/CloudFlare-DDNS-Agent
# Description:   Dynamic DNS agent for the CloudFlare API.

# Global imports.
import sys
import requests
import json
import logging
import socket
import ConfigParser
import argparse
import os

# Global vars.
PROG_NAME = 'CloudFlare DDNS Agent'

# Logging config.
logging.basicConfig(  # Define logging format.
    format=PROG_NAME + ' : %(levelname)s : %(message)s',
    # Set logging location.
    filename='/var/log/cloudflare-ddns-agent.log',  # Set logging level.
    level=logging.DEBUG)


# Description: Parse arguments from the command-line.
def parseArgs():
    try:
        # Create parser and a required arguments group.
        parser = argparse.ArgumentParser(
            description='Dynamic DNS agent for the CloudFlare API.')
        requiredArgs = parser.add_argument_group('required arguments')

        # Define required arguments.
        requiredArgs.add_argument('-c', '--config',
                                  help='Path to the config file.',
                                  required=True)

        # Parse and return the arguments.
        args = parser.parse_args()
        return args

    except:
        logging.error('Error parsing command-line arguments. Exiting.')

    sys.exit(1)


# Description: Check a generic HTTP status code.
def checkHttpResponse(code):
    try:
        # If HTTP status is OK then return immediately.
        if code == 200:
            logging.debug('Server returned: 200 - OK.')
            return
        # Otherwise, log appropriate error and exit.
        elif code == 400:
            logging.error('Server returned: 400 - Bad Request. Exiting.')
        elif code == 401:
            logging.error('Server returned: 401 - Unauthorised. Exiting.')
        elif code == 403:
            logging.error('Server returned: 403 - Forbidden. Exiting.')
        elif code == 404:
            logging.error('Server returned: 404 - Not Found. Exiting.')
        elif code == 410:
            logging.error('Server returned: 410 - Gone. Exiting.')
        elif code == 500:
            logging.error(
                'Server returned: 500 - Internal Server Error. Exiting.')
        elif code == 501:
            logging.error('Server returned: 501 - Not Implemented. Exiting.')
        elif code == 503:
            logging.error(
                'Server returned: 503 - Service Unavailable. Exiting.')
        elif code == 550:
            logging.error('Server returned: 550 - Permission Denied. Exiting.')
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
        responseJson = json.loads(response.text)

    except:
        logging.error('Error parsing HTTP response body to JSON. Exiting.')
        sys.exit(1)

    try:
        # If result is success, return immediately.
        if responseJson["result"] == 'success':
            logging.info('API result: Success.')
            return

        # Otherwise, log the error and exit.
        elif responseJson["result"] == 'error':
            logging.error("CloudFlare API: %s - %s." %
                          (responseJson['err_code'], responseJson['msg']))

        else:
            logging.error('Unhandled response from CloudFlare API. Exiting.')

    except:
        logging.error('Error analysing the JSON response body. Exiting.')

    sys.exit(1)


# Description: Returns WAN IP of the host.
def getWanIp(ipResolver):
    logging.info("Obtaining WAN IP from '%s'..." % ipResolver)

    try:
        # Attempt GET request to resolver.
        response = requests.get(ipResolver)

        # If HTTP status code isn't OK, log error and exit immediately.
        checkHttpResponse(response.status_code)

    except:
        logging.error("Error obtaining WAN IP from '%s'." % ipResolver)
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
        logging.error("Invalid WAN IP obtained from '%s'." % ipResolver)

    except:
        logging.error("Error validating WAN IP from '%s'." % ipResolver)

    sys.exit(1)


# Description: Get all of our existing DNS records from CloudFlare API.
def getRecords(apiKey, email, zone, apiUrl):
    logging.info('Obtaining existing DNS records from CloudFlare API...')

    # Construct payload.
    payload = {'a': 'rec_load_all', 'tkn': apiKey, 'email': email, 'z': zone, }

    try:
        # Perform the GET request.
        response = requests.get(apiUrl, params=payload)

        # If API response isn't good, log error and exit immediately.
        checkApiResponse(response)

    except:
        logging.error('Error obtaining DNS records from CloudFlare API.')
        sys.exit(1)

    try:
        recordsJson = json.loads(response.text)
        response.close()

        logging.info("Obtained %i DNS records from CloudFlare API." %
                     recordsJson['response']['recs']['count'])

        return recordsJson

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
        'a': 'rec_edit',
        'tkn': API_KEY,
        'email': EMAIL,
        'z': ZONE,
        'type': 'A',
        'id': recordId,
        'name': name,
        'content': wanIp,
        'ttl': 1,
        'service_mode': 1,
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


# Description: Compare the logged IP with the current IP to determine if a DNS update is required.
def checkIpLog(ipLogPath, wanIp):
    try:
        # If the IP log exists.
        if os.path.isfile(ipLogPath):
            logging.debug(
                'IP log exists. Comparing logged IP with current WAN IP.')

            # Read in the logged IP.
            with open(ipLogPath, "a+") as ipLog:
                loggedIp = ipLog.read()

            # Throw an exception if the logged IP is invalid/corrupt.
            socket.inet_aton(loggedIp)

            # If the current WAN IP matches the logged IP, nothing more to do.
            if wanIp == loggedIp:
                logging.info("Current IP matches logged IP (%s)." % wanIp)
                return False

            # Otherwise, write the current WAN IP to the IP log and continue.
            else:
                logging.info("Current IP (%s) does not match logged IP (%s)." %
                             (wanIp, loggedIp))

                with open(ipLogPath, "w") as ipLog:
                    ipLog.write("%s" % wanIp)

                return True

        # Otherwise, create the file, log the current WAN IP and continue.
        else:
            logging.info(
                'IP log does not exist (first run or system rebooted). DNS update will run.')
            with open(ipLogPath, "w") as ipLog:
                ipLog.write("%s" % wanIp)

            return True

    except IOError:
        logging.error("Error trying to read or create '%s'." % ipLogPath)

    except socket.error:
        logging.error("Invalid logged IP obtained from '%s'." % ipLogPath)

    except:
        logging.error("Error while processing IP log (%s)." % ipLogPath)

    sys.exit(1)


# Description: Load values from config file.
def loadConfig(configPath):
    logging.info("Loading agent config from '%s'..." % configPath)

    try:
        # Initialise a ConfigReader and read in agent.conf
        config = ConfigParser.ConfigParser()
        config.read(configPath)

        # Read Authentication section
        email = config.get('Authentication', 'Email')
        apiKey = config.get('Authentication', 'ApiKey')
        zone = config.get('Authentication', 'Zone')

        # Read General section
        updateZone = config.get('General', 'UpdateZone')

        # Read Endpoints section
        cfApiUrl = config.get('Endpoints', 'CfApiUrl')
        ipResolver = config.get('Endpoints', 'IpResolver')

        # Read Logs section
        runLog = config.get('Logs', 'RunLog')
        ipLog = config.get('Logs', 'IpLog')

        # Output to log for debugging.
        logging.debug(" - Email              : %s" % email)
        logging.debug(" - API key            : %s" % apiKey)
        logging.debug(" - Zone               : %s" % zone)
        logging.debug(" - Update Zone?       : %s" % updateZone)
        logging.debug(" - CloudFlare API URL : %s" % cfApiUrl)
        logging.debug(" - IP Resolver URL    : %s" % ipResolver)
        logging.debug(" - Run log location   : %s" % runLog)
        logging.debug(" - IP log location    : %s" % ipLog)

        logging.info('Loaded agent config successfully.')
        return config._sections

    except KeyError:
        logging.error("Missing key in config (%s). Exiting." % configPath)

    except ValueError:
        logging.error("Missing value in config (%s). Exiting." % configPath)

    except:
        logging.error("Error while parsing config (%s). Exiting." % configPath)

    sys.exit(1)


# Description: Orchestrate the whole operation.
def main():
    #    try:
    # Parse arguments from the command line.
    args = parseArgs()

    # Then load in values from the config file.
    config = loadConfig(args.config)

    # Then get our current WAN IP.
    wanIp = getWanIp(config['Endpoints']['ipresolver'])

    # Then check if that IP has changed since the last run. If not, exit.
    updateRequired = checkIpLog(config['Logs']['iplog'], wanIp)

    if updateRequired == True:
        logging.info('DNS update is required.')

    elif updateRequired == False:
        logging.info('DNS update is not required.')
        sys.exit(0)

    else:
        logging.error('Error while determining if DNS update is required.')
        sys.exit(1)

    # If it has, get all existing DNS records from CloudFlare.
    records = getRecords(config['Authentication']['apikey'],
                         config['Authentication']['email'],
                         config['Authentication']['zone'],
                         config['Endpoints']['cfapiurl'])
    
    # Then for each of our records.
    #    for name in config[]:
    # Get the record ID.
    #        recordId = getRecordId(name)

    # And update the it with our new IP.
    #        updateRecord(name, recordId)

    #    except:
    #        logging.error('Something bad happened in main. Exiting.')

    return


logging.info('DDNS update started...')

# Orchestrate the whole operation.
main()

# Exit
logging.info('DDNS update completed.')
sys.exit(0)
