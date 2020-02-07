import sys
import json
import urllib2

from fnmatch import fnmatch


def send_notification(payload):
    settings = payload.get('configuration')
    print >> sys.stderr, "DEBUG Sending incident with settings %s" % settings

    url = settings.get('integration_url_override')

    if not url:
        url = settings.get('integration_url')

    # check if only the integration key was given
    if len(url) == 32:
        url = 'https://events.pagerduty.com/integration/' + url + "/enqueue"

    if not url.startswith("https://"):
        print >> sys.stderr, "ERROR URL scheme must be https : %s" % (url)
        return False

    del payload['session_key']

    body = json.dumps(payload)

    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)

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
