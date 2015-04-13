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
import logging.handlers
import socket
import yaml
import argparse
import os
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE
import netifaces

# Logging config.
ddnsLog = logging.getLogger('ddnsLog')
ddnsLog.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log')
ddnsLog.addHandler(handler)


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
        ddnsLog.error('Error parsing command-line arguments. Exiting.')

    sys.exit(1)


# Description: Check a generic HTTP status code.
def checkHttpResponse(code):
    try:
        # If HTTP status is OK then return immediately.
        if code == 200:
            ddnsLog.debug('Server returned: 200 - OK.')
            return
        # Otherwise, log appropriate error and exit.
        elif code == 400:
            ddnsLog.error('Server returned: 400 - Bad Request. Exiting.')
        elif code == 401:
            ddnsLog.error('Server returned: 401 - Unauthorised. Exiting.')
        elif code == 403:
            ddnsLog.error('Server returned: 403 - Forbidden. Exiting.')
        elif code == 404:
            ddnsLog.error('Server returned: 404 - Not Found. Exiting.')
        elif code == 410:
            ddnsLog.error('Server returned: 410 - Gone. Exiting.')
        elif code == 500:
            ddnsLog.error(
                'Server returned: 500 - Internal Server Error. Exiting.')
        elif code == 501:
            ddnsLog.error('Server returned: 501 - Not Implemented. Exiting.')
        elif code == 503:
            ddnsLog.error(
                'Server returned: 503 - Service Unavailable. Exiting.')
        elif code == 550:
            ddnsLog.error('Server returned: 550 - Permission Denied. Exiting.')
        else:
            ddnsLog.error("%i - Unrecognised HTTP return code. Exiting." % code)

    except:
        ddnsLog.error('Error parsing HTTP return code. Exiting.')

    sys.exit(1)


# Description: Check a CloudFlare API HTTP response.
def checkApiResponse(response):
    # If HTTP status code isn't OK, log error and exit immediately.
    checkHttpResponse(response.status_code)

    # Otherwise, parse response body to JSON.
    try:
        responseJson = json.loads(response.text)

    except:
        ddnsLog.error('Error parsing HTTP response body to JSON. Exiting.')
        sys.exit(1)

    try:
        # If result is success, return immediately.
        if responseJson["result"] == 'success':
            ddnsLog.info('API result: Success.')
            return

        # Otherwise, log the error and exit.
        elif responseJson["result"] == 'error':
            ddnsLog.error("CloudFlare API: %s - %s." %
                          (responseJson['err_code'], responseJson['msg']))

        else:
            ddnsLog.error('Unhandled response from CloudFlare API. Exiting.')

    except:
        ddnsLog.error('Error analysing the JSON response body. Exiting.')

    sys.exit(1)


# Description: Returns WAN IP of the host.
def getWanIp(ipResolver):
    ddnsLog.info("Obtaining WAN IP from '%s'..." % ipResolver)

    try:
        # Attempt GET request to resolver.
        response = requests.get(ipResolver)

        # If HTTP status code isn't OK, log error and exit immediately.
        checkHttpResponse(response.status_code)

    except:
        ddnsLog.error("Error obtaining WAN IP from '%s'." % ipResolver)
        sys.exit(1)

    try:
        # Otherwise, try to extract the IP.
        wanIp = response.text.strip()
        response.close()

        # Throw an exception if the IP is invalid.
        socket.inet_aton(wanIp)

        # If we've made it this far we can happily return our WAN IP.
        ddnsLog.info("WAN IP resolved as: %s" % wanIp)
        return wanIp

    except socket.error:
        ddnsLog.error("Invalid WAN IP obtained from '%s'." % ipResolver)

    except:
        ddnsLog.error("Error validating WAN IP from '%s'." % ipResolver)

    sys.exit(1)


# Description: Get all of our existing DNS records from CloudFlare API.
def getRecords(apiKey, email, zone, apiUrl):
    ddnsLog.info('Obtaining existing DNS records from CloudFlare API...')

    # Construct payload.
    payload = {'a': 'rec_load_all', 'tkn': apiKey, 'email': email, 'z': zone, }

    try:
        # Perform the GET request.
        response = requests.get(apiUrl, params=payload)

        # If API response isn't good, log error and exit immediately.
        checkApiResponse(response)

    except:
        ddnsLog.error('Error obtaining DNS records from CloudFlare API.')
        sys.exit(1)

    try:
        recordsJson = json.loads(response.text)
        response.close()

        ddnsLog.info("Obtained %i DNS records from CloudFlare API." %
                     recordsJson['response']['recs']['count'])

        return recordsJson

    except:
        ddnsLog.error('Error parsing records to JSON. Exiting.')

    sys.exit(1)


# Description: Return ID of a given record name.
def getRecordId(records, name):
    ddnsLog.info("Searching for record ID of: %s" % name)

    try:
        # Search records for the required name.
        for record in records['response']['recs']['objs']:
            # When found, return its ID.
            if record['display_name'] == name:
                ddnsLog.info("Obtained record ID: %s" % record['rec_id'])
                return record['rec_id']

                # If we're here, we couldn't find the record name.
        ddnsLog.error("Could not find a record matching: %s" % name)

    except:
        ddnsLog.error('Error while searching for record. Exiting.')

    sys.exit(1)


# Description: Update a given record with our new IP address.
def updateRecord(ipAddr, name, recordId, apiKey, email, zone, apiUrl):
    ddnsLog.info("Updating '%s' to point at '%s'..." % (name, ipAddr))

    # Construct payload.
    payload = {
        'a': 'rec_edit',
        'tkn': apiKey,
        'email': email,
        'z': zone,
        'type': 'A',
        'id': recordId,
        'name': name,
        'content': ipAddr,
        'ttl': 1,
        'service_mode': 1,
    }

    try:
        # Try to update the record.
        response = requests.get(apiUrl, params=payload)

        # If API response isn't good, log error and exit immediately.
        checkApiResponse(response)

        # Otherwise, log success and return.
        ddnsLog.info('Record updated successfully.')
        return

    except:
        ddnsLog.error('Error updating record via CloudFlare API.')

    sys.exit(1)


# Description: Compare the logged IP with the current IP to determine if a DNS update is required.
def checkIpLog(ipLogPath, ipAddr):
    try:
        # If the IP log exists.
        if os.path.isfile(ipLogPath):
            ddnsLog.debug(
                'IP log exists. Comparing logged IP with current IP address.')

            # Read in the logged IP.
            with open(ipLogPath, "r") as ipLog:
                loggedIp = ipLog.read()

            # Throw an exception if the logged IP is invalid/corrupt.
            socket.inet_aton(loggedIp)

            # If the current IP address matches the logged IP, nothing more to do.
            if ipAddr == loggedIp:
                ddnsLog.info("Current IP matches logged IP (%s)." % ipAddr)
                return False

            # Otherwise, write the current IP address to the IP log and continue.
            else:
                ddnsLog.info("Current IP (%s) does not match logged IP (%s)." %
                             (ipAddr, loggedIp))

                with open(ipLogPath, "w") as ipLog:
                    ipLog.write("%s" % ipAddr)

                return True

        # Otherwise, create the file, log the current IP address and continue.
        else:
            ddnsLog.info(
                'IP log does not exist (first run or system rebooted). DNS update will run.')
            with open(ipLogPath, "w") as ipLog:
                ipLog.write("%s" % ipAddr)

            return True

    except IOError:
        ddnsLog.error("Error trying to read or create '%s'." % ipLogPath)

    except socket.error:
        ddnsLog.error("Invalid logged IP obtained from '%s'." % ipLogPath)

    except:
        ddnsLog.error("Error while processing IP log (%s)." % ipLogPath)

    # If there's an error, remove the IP log as to not prevent the next run.
    try:
        os.remove(ipLogPath)
    except:
        ddnsLog.error("Error while trying to remove IP log (%s)." % ipLogPath)

    sys.exit(1)


# Description: Load values from config file.
def loadConfig(configPath):
    ddnsLog.info("Loading agent config from '%s'..." % configPath)

    try:
        # Open config.yaml
        configFile = open(configPath)

        # Parse config.yaml to YAML.
        configDict = yaml.safe_load(configFile)

        # Close config.yaml
        configFile.close()

        # Mandatory keys.
        requiredKeys = ['authentication', 'general', 'records', 'endpoints',
                        'logs']

        # For each required key.
        for rKey in requiredKeys:

            # If a match is found in configDict, happy days.
            if rKey in configDict:
                ddnsLog.debug("Found mandatory config key '%s' in '%s'." %
                              (rKey, configPath))

            # Otherwise, log error and exit.
            else:
                ddnsLog.error(
                    "Could not find mandatory config key '%s' in '%s'." %
                    (rKey, configPath))
                sys.exit(1)

        # Return config dict.
        ddnsLog.info('Loaded agent config successfully.')
        return configDict

    except:
        ddnsLog.error("Error while parsing config (%s). Exiting." % configPath)

    sys.exit(1)


# Description: Return the IP address of the given network interface.
def getInterfaceIp(interface):
    try:
        ddnsLog.info("Obtaining IP address of '%s'..." % interface)
        ipAddr = netifaces.ifaddresses(interface)[AF_INET][0]['addr']
        ddnsLog.info("IP address of '%s' is '%s'." % (interface, ipAddr))

        return ipAddr

    except:
        ddnsLog.error(
            "Error while obtaining IP address of '%s'. Exiting." % interface)

    sys.exit(1)


# Description: Orchestrate the whole operation.
def main():
    # Parse arguments from the command line.
    args = parseArgs()

    # Then load in values from the config file.
    config = loadConfig(args.config)

    # If interface is set to WAN in config.yaml get WAN IP.
    if config['general']['interface'] == 'WAN':
        ddnsLog.info('Interface config is set to WAN.')
        ipAddr = getWanIp(config['endpoints']['ipResolver'])

    # Otherwise, get IP of the given local interface.
    else:
        ddnsLog.info('Interface config set to local interface.')
        ipAddr = getInterfaceIp(config['general']['interface'])

    # Then check if that IP has changed since the last run. If not, exit.
    updateRequired = checkIpLog(config['logs']['ipLog'], ipAddr)

    if updateRequired == True:
        ddnsLog.info('DNS update is required.')

    elif updateRequired == False:
        ddnsLog.info('DNS update is not required.')
        sys.exit(0)

    else:
        ddnsLog.error('Error while determining if DNS update is required.')
        sys.exit(1)

    # If it has, get all existing DNS records from CloudFlare.
    records = getRecords(config['authentication']['apiKey'],
                         config['authentication']['email'],
                         config['authentication']['zone'],
                         config['endpoints']['apiUrl'])

    # Then for each record defined in config.yaml
    for name in config['records']:
        # Get the record ID.
        recordId = getRecordId(records, name)

        # And update it with our new IP address.
        updateRecord(
            ipAddr, name, recordId, config['authentication']['apiKey'],
            config['authentication']['email'],
            config['authentication']['zone'], config['endpoints']['apiUrl'])

    return


ddnsLog.info('Agent run started...')

# Orchestrate the whole operation.
main()

# Exit
ddnsLog.info('Agent run completed.')
sys.exit(0)
