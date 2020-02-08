import sys
import json
import urllib2

from fnmatch import fnmatch

# generate the JSON for the incident
# Details: https://v2.developer.pagerduty.com/docs/events-api-v2 
# Example: https://v2.developer.pagerduty.com/docs/send-an-event-events-api-v2
def generate_inc(details, key):
    inc = {}
    payload = {}

    # determine if triggering or resolving
    eventType = details['search_name'].split()[-1]
    if eventType != "resolve":
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
    print >> sys.stderr, "DEBUG Sending incident with settings %s" % settings

    url = "https://events.pagerduty.com/v2/enqueue"
    key = settings.get('integration_key_override')

    if not key:
        key = settings.get('integration_key')

    # check if only the integration key was given
    if not len(key) == 32:
        print >> sys.stderr, "ERROR Integration KEY must be 32 characters long"
        return False

    # delete session key
    del details['session_key']

    # generate incident json
    inc = generate_inc(details, key)
    body = json.dumps(inc)

    # send PagerDuty incident info
    print >> sys.stderr, 'INFO Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})

    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO PagerDuty server responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG PagerDuty server response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s (%s)" % (e, str(dir(e)))
        print >> sys.stderr, "ERROR Server response: %s" % e.read()
        return False



if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = send_notification(payload)
        if not success:
            print >> sys.stderr, "FATAL Failed trying to incident alert"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO Incident alert notification successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
