#!/bin/python3
import sys
import json

import urllib.request
import urllib.error

# This is the file that will store information about the latest successful
# trigger and resolve requests sent to PagerDuty. If you wish to save the file


# generate the JSON for the incident
# Details: https://v2.developer.pagerduty.com/docs/events-api-v2 
# Example: https://v2.developer.pagerduty.com/docs/send-an-event-events-api-v2
def generate_inc(details, settings, key):
    inc = {}
    payload = {}

    resolveKeyword = settings.get('resolve_keyword')
    keywordLocation = settings.get('resolve_keyword_location') # [0: back | 1: front]

    # determine if triggering or resolving
    eventType = details['search_name'].rsplit(' ', 1)[1 - keywordLocation]

    # create incident JSON
    if eventType == resolveKeyword:
        eventType = "resolve"
        details['search_name'] = details['search_name'].rsplit(' ', 1)[keywordLocation]
    else:
        # add trigger specific parameters
        eventType = "trigger"
   
        payload['summary'] = details['result']['host'] + " " + details['search_name']
        payload['severity'] = "critical"
        payload['source'] = details['result']['host']
        payload['component'] = details['result']['_sourcetype']
        payload['group'] = details['result']['index']
        payload['custom_details'] = details['result']

        # create incident JSON
        inc['payload'] = payload
        inc['client'] = "Splunk"
        inc['client_url'] = details['results_link']

    # computer dedup_key
    dedup_key = details['search_name'] + " (Server: " + details['result']['host'] + ")"
    if len(dedup_key) > 255:
        dedup_key = dedup_key[0 : 254]

    # add general incident parameters
    inc['routing_key'] = key
    inc['dedup_key'] = dedup_key
    inc['event_action'] = eventType

    return inc



def send_notification(details):

    global timestamps

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
        return False, None, None

    # generate incident json
    inc = generate_inc(details, key)
    eventType = inc['event_action']
    body = json.dumps(inc).encode("utf-8")
    json.dump(inc, open("test.json","w"))

    # if event is a resolve, then check if we need to send (truth table in readme)
    if inc['event_action'] == "resolve":
        if send_check(inc, details['session_key']):
            return -1, None, None

    #ssl._create_default_https_context = ssl._create_unverified_context

    # send PagerDuty incident info
    print('DEBUG Calling url="{:s}" with body={:s}'.format(url, body.decode()), file=sys.stderr)
    req = urllib.request.Request(url=url, data=body, headers={"Content-Type": "application/json"})

    try:
        res = urllib.request.urlopen(req, cafile="/etc/pki/tls/certs/ca-bundle.crt")
        body = res.read().decode("utf-8")
        print("INFO PagerDuty server responded with HTTP status = {:d}".format(res.code), file=sys.stderr)
        print("DEBUG PagerDuty server response: {:s}".format(body), file=sys.stderr)
        timestamps[inc['dedup_key']][eventType] = str(datetime.now())
        return 200 <= res.code < 300, inc['event_action'], inc['dedup_key']
    except urllib.error.HTTPError as e:
        print("ERROR Error sending message: {:s} ({:s})".format(e, str(dir(e))), file=sys.stderr)
        print("ERROR Server response: {:s}".format(e.read()), file=sys.stderr)
        return False, None, None



if __name__ == "__main__":

    sys.stdout = open('/tmp/output', 'w')
    sys.stderr = open('/tmp/error', 'w')

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success, action, dedup_key = send_notification(payload)
        if success == -1:
            print("INFO Cache indicates no open tickets to resolve")
            sys.exit(0)
        elif not success:
            print("FATAL Failed trying to incident alert", file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO {:s} {:s} successfully sent".format(dedup_key, action), file=sys.stderr)
            
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
