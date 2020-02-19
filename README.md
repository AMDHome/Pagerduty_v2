# Pagerduty_v2
A Custom Pagerduty Integration for splunk

## Setup
### Requirements
In order to use this app, you will need the following:

1. A pagerduty integration key. You can extract it from the Splunk Integration URL
	- Instructions: https://www.pagerduty.com/docs/guides/splunk-security-integration-guide/
2. A Splunk user account. Needs to be able to perform searches and post http-simple requests to Splunk.
3. The pagerduty_v2.tar.gz file that can be found in the releases section of this github.

### Instructions
1. Log into Splunk and click the gear icon next to `Apps` in the left hand sidebar
2. Click on `Install app from file` in the upper-right corner
3. Choose the `pagerduty_v2.tar.gz` file that you downloaded from github and click `Upload` and then `Restart Splunk`
4. Once Splunk finishes restarting, relog in and go to `Settings` > `Alert Actions` > `Setup PagerDuty`
5. Fill in the fields in the setup and click save. For more information read the Additional Information (Settings) section below.
6. Have fun setting up your alerts.

### Notes On Creating Alerts
#### Alert Once vs. For each result
If you have your alert trigger for each result then it will send out multiple pages to PagerDuty. Pagerduty will then log them all and put them into 1 incident. If you set the trigger to only alert once then it will only send the data from the last search result to PagerDuty. If you have multiple search results pop up for your alert you could lose information if you select to only trigger once. 

#### Alerts For Lack of Results
If you are alerting for the lack of search results then make sure you are very specific with your alert title. As there is no search results, Splunk does not send us any useful information other then the alert name. Make sure you put all relevent information in the alert name or you will end up with a vague incident on PagerDuty

### Additional Information (Settings)
#### Integration Key
Make sure you enter your 32 character integration key. The script will not work if you enter the integration URL. You can extract the integration key from the url by copying out the string of characters.

#### Splunk User
If you try to update your username and account it will produce the following error:
```
Encountered the following error while trying to update: Error while posting to url=/servicesNS/nobody/pagerduty_v2/storage/passwords/
```
This is an issue with how Splunk handles stored passwords. In order to update the password you will need to delete `$SPLUNK_HOME$/etc/apps/pagerduty_v2/local/passwords.conf` and restart splunk. It is a pain. Sorry. #BlameSplunkNotMe

#### Resolve Keyword
As Splunk has no good way to tie trigger and resolve alerts together, we do this buy using a keyword in the Alert Name. You can set this keyword to whatever you want. This keyword must be either the first or the last word of the name depending on the Resolve Keyword Location field. 

For Example:
Let's say you set the resolve keyword to `chicken`.
The following alerts will trigger and resolve the PagerDuty incident named `Server XYZ is Down` respectively:

```
Trigger Alert Name: Server XYZ is Down
Resolve Alert Name: Server XYZ is Down chicken
```

This example is for entertainment purposes only. A more realistic keyword would be the word "resolver" but you can put anything you want. If you are not planning to have Splunk resolve your tickets, you can just leave this blank.

#### Resolve Keyword Location
By default, the keyword is set to be the last word of the alert name. If you wish to put the keyword in the front you can select this checkbox to move it to the front. If we use the same example as above the Alert names would now be:

```
Trigger Alert Name: "Server XYZ is Down"
Resolve Alert Name: "chicken Server XYZ is Down"
```

## Logs
This PagerDuty script will log the result of every set of attempts to contact PagerDuty. You can view these in splunk by searching the following:
```
index="pagerduty"
```

You can search the logs for successes or failures by specifying the sourcetype. The valid sourcetypes are: `trigger.sent`, `trigger.failed`, `resolve.sent`, `resolve.failed`. For the failed sourcetypes, The message will tell you exactly the type of failure that occoured. 

Splunk also logs the status everytime it runs the script. To view the Splunk logs for the script, you can search the following
```
index=_internal action="pagerduty"
```

## Notes
### PagerDuty Index
This script will create the data index "pagerduty" and put status information to it automatically. You do not need to create it yourself.

### PagerDuty Dedup key
PagerDuty does not keep track of incidents by the name of the incident. They use something called a deduplication key (dedup key). For our purposes, the alert name will be both the PagerDuty incident name and the dedup key. This means that every alert for every check on every server will need a different alert name. For instance you cannot just create a single Ping Test and Ping Test resolver alert for all of your systems. You will need to create them for each indivisual servers each with a different name. Yes this means you will have a ton of alerts if you are monitoring a lot of machines, but really you shouldn't be using Splunk to monitor servers in the first place.

### Failed To Send Alert
If something goes wrong with sending the alert to PagerDuty, the script will retry twice (total send attemps = 3). It will try 2 seconds after the initial send and then 4 seconds after the initial send. It will give up after the third attempt to contact PagerDuty fails. You may wish to create an alert to monitor the trigger.failed and resolve.failed sorucetypes and have splunk email you about the failures.
