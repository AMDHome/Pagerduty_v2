#!/bin/python3

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl

from fnmatch import fnmatch

SSL_CERT_DIR="/etc/ssl/certs"

# generate the JSON for the incident
# Details: https://v2.developer.pagerduty.com/docs/events-api-v2 
# Example: https://v2.developer.pagerduty.com/docs/send-an-event-events-api-v2
def generate_inc(details, key):
    inc = {}
    payload = {}

    # determine if triggering or resolving
    eventType = details['search_name'].rsplit(' ', 1)[1]
    if eventType == "resolve":
        details['search_name'] = details['search_name'].rsplit(' ', 1)[0]
    else:
        eventType = "trigger"

    # create JSON Payload
    payload['summary'] = details['result']['host'] + " " + details['search_name']
    payload['severity'] = "critical"
    payload['source'] = details['result']['host']
    payload['component'] = details['result']['_sourcetype']
    payload['group'] = details['result']['index']
    payload['custom_details'] = details['result']

    dedup_key = details['search_name'] + " (Server: " + details['result']['host'] + ")"
    if len(dedup_key) > 255:
        dedup_key = dedup_key[0 : 254]

    # create incident JSON
    inc['payload'] = payload
    inc['routing_key'] = key
    inc['dedup_key'] = dedup_key
    inc['event_action'] = eventType
    inc['client'] = "Splunk"
    inc['client_url'] = details['results_link']

    return inc



def send_notification(details):

    # get integration API key
    settings = details.get('configuration')
    print("DEBUG Sending incident with settings", settings, file=sys.stderr)

    url = "https://events.pagerduty.com/v2/enqueue"
    key = settings.get('integration_key_override')

    if not key:
        key = settings.get('integration_key')

    # check if only the integration key was given
    if not len(key) == 32:
        print("ERROR Integration KEY must be 32 characters long", file=sys.stderr)
        return False

    # delete session key
    del details['session_key']

    # generate incident json
    inc = generate_inc(details, key)
    eventType = inc['event_action']
    body = json.dumps(inc).encode("utf-8")

    #Ignore Certs
    ssl._create_default_https_context = ssl._create_unverified_context


    # send PagerDuty incident info
    print('DEBUG Calling url="{:s}" with body={:s}'.format(url, body.decode()), file=sys.stderr)
    req = urllib.request.Request(url=url, data=body, headers={"Content-Type": "application/json"})

    try:
        res = urllib.request.urlopen(req)
        body = res.read().decode("utf-8")
        print("INFO PagerDuty server responded with HTTP status = {:d}".format(res.code), file=sys.stderr)
        print("DEBUG PagerDuty server response: {:s}".format(body), file=sys.stderr)
        return 200 <= res.code < 300
    except urllib.error.HTTPError as e:
        print("ERROR Error sending message: {:s} ({:s})".format(e, str(dir(e))), file=sys.stderr)
        print("ERROR Server response: {:s}".format(e.read()), file=sys.stderr)
        return False



if __name__ == "__main__":

    sys.stdout = open('/tmp/output', 'w')
    sys.stderr = open('/tmp/output', 'w')

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = send_notification(payload)
        if not success:
            print("FATAL Failed trying to incident alert", file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Incident alert notification successfully sent", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
