#!/bin/python3
import sys, os
import json
import time

import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client

import splunk.entity as entity

splunkService = None

# generate the JSON for the incident
# Details: https://v2.developer.pagerduty.com/docs/events-api-v2 
# Example: https://v2.developer.pagerduty.com/docs/send-an-event-events-api-v2
def generate_inc(details, settings, key):
    inc = {}
    payload = {}

    resolveKeyword = settings.get('resolve_keyword')
    keywordLocation = int(settings.get('resolve_keyword_location')) # [0: back | 1: front]

    if keywordLocation == 0:
        splitName = details['search_name'].rsplit(' ', 1)
    else:
        splitName = details['search_name'].split(' ', 1)

    # determine if triggering or resolving
    eventType = splitName[1 - keywordLocation]

    # create incident JSON
    if eventType == resolveKeyword:
        eventType = "resolve"
        details['search_name'] = splitName[keywordLocation]
    else:
        # add trigger specific parameters
        eventType = "trigger"

        # if there are results   
        if details['result']:
            payload['summary'] = details['result']['host'] + " " + details['search_name']
            payload['source'] = details['result']['host']
            payload['component'] = details['result']['_sourcetype']
            payload['group'] = details['result']['index']
        else:
            payload['summary'] = details['search_name']
            payload['source'] = "unknown"

        payload['custom_details'] = details['result']
        payload['severity'] = "critical"

        # create incident JSON
        inc['payload'] = payload
        inc['client'] = "Splunk"
        inc['client_url'] = details['results_link']

    # computer dedup_key
    dedup_key = details['search_name']
    if len(dedup_key) > 255:
        dedup_key = dedup_key[0 : 254]

    # add general incident parameters
    inc['routing_key'] = key
    inc['dedup_key'] = dedup_key
    inc['event_action'] = eventType

    return inc



# gets stored encrypted login credentials
def getCredentials(sessionKey):
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace='pagerduty_v2',
                                      owner='nobody', sessionKey=sessionKey)
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s"
                        % (myapp, str(e)))

   # return first set of credentials
    for i, c in entities.items():
        return c['username'], c['clear_password']

    raise Exception("No credentials have been found")



# checks the logs in splunk to determine if incident has been closed by splunk
# returns True: Closed, no need send resolve, False: send resolve
def send_check(inc, sessionKey):

    global splunkService

    triggerTime = ""
    resolveTime = ""
    search_args = {"earliest_time": "-1q", "latest_time": "now", "output_mode": "json"}

    search_query = "search index=\"pagerduty\" sourcetype=\"trigger.sent\" \"" + inc['dedup_key'] + "\" | head 1"
    res = json.loads(splunkService.jobs.oneshot(search_query, **search_args).read())
    
    if res["results"]:
        triggerTime = res["results"][0]["_time"]

    search_query = "search index=\"pagerduty\" sourcetype=\"resolve.sent\" \"" + inc['dedup_key'] + "\" | head 1"
    res = json.loads(splunkService.jobs.oneshot(search_query, **search_args).read())
    
    if res["results"]:
        resolveTime = res["results"][0]["_time"]

    return triggerTime < resolveTime



def send_notification(details):

    global splunkService
    username, password = getCredentials(details['session_key'])
    splunkService = client.connect(username=username, password=password)
    pagerdutyIndex = splunkService.indexes["pagerduty"]

    # get integration API key
    settings = details.get('configuration')

    url = "https://events.pagerduty.com/v2/enqueue"
    key = settings.get('integration_key_override')

    if not key:
        key = settings.get('integration_key')

    # check if only the integration key was given
    if not len(key) == 32:
        print("ERROR Integration KEY must be 32 characters long", file=sys.stderr)
        return False, None, None

    # generate incident json
    inc = generate_inc(details, settings, key)
    eventType = inc['event_action']
    body = json.dumps(inc).encode("utf-8")
    json.dump(inc, open("test.json","w"))

    # if event is a resolve, then check if we need to send (truth table in readme)
    if inc['event_action'] == "resolve":
        if send_check(inc, details['session_key']):
            return -1, None, None

    # send PagerDuty incident info
    print('DEBUG Calling url="{:s}" with body={:s}'.format(url, body.decode()), file=sys.stderr)
    req = urllib.request.Request(url=url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"})


    # try to send notification (will try 3 times: Immediately, after 2 seconds, after 4 seconds)
    # Dont retry on HTTP code 202 (success) or 400 (failed: bad JSON)
    # retry on all other errors
    interval = 2
    lastException = None
    for _ in range(3):
        try:
            res = urllib.request.urlopen(req)
            body = res.read().decode()

            # Success
            srctype = eventType + ".sent"
            eventType += "d" if eventType[-1] == 'e' else "ed"
            pagerdutyIndex.submit("Successfully " + eventType + " incident for " + inc['dedup_key'] + " on PagerDuty", sourcetype=srctype)
            return 200 <= res.code < 300, inc['event_action'], inc['dedup_key']

        except urllib.error.HTTPError as e:

            # If HTTP returns error 400 (Bad JSON) just stop
            if e.code == 400:
                print("ERROR Server response:", e, "{:s}".format(e.read().decode("utf-8")), file=sys.stderr)
                srctype = eventType + ".failed"
                pagerdutyIndex.submit("Failed to " + eventType + " incident for " + inc['dedup_key'] + " on PagerDuty: ERROR 400 (Bad JSON)", sourcetype=srctype)
                return False, None, None

            lastException = e

        time.sleep(interval)
        interval *= 2

    # if it gets to here that means the HTTP request failed 3 times.
    print("ERROR Server response:", lastException, "{:s}".format(lastException.read().decode("utf-8")), file=sys.stderr)
    srctype = eventType + ".failed"
    if lastException.code == 429:
        eMsg = "429 (Too many API calls at a time)"
    else:
        eMsg = str(lastException.code) + " (Internal Server Error)"
    pagerdutyIndex.submit("Failed to " + eventType + " incident for " + inc['dedup_key'] + " on PagerDuty: ERROR " + eMsg, sourcetype=srctype)
    return False, None, None



if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success, action, dedup_key = send_notification(payload)
        if success == -1:
            print("INFO Cache indicates no open tickets to resolve", file=sys.stderr)
            sys.exit(0)
        elif not success:
            print("FATAL Failed trying to send incident alert", file=sys.stderr)
            sys.exit(2)
        else:
            print("DEBUG {:s} {:s} successfully sent".format(dedup_key, action), file=sys.stderr)
            
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
