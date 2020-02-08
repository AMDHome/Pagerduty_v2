# Pagerduty_v2
A Custom Pagerduty Integration for splunk

# Examples of `details` passed by Splunk
``` JSON
details={
	"results_link": "http://splunk-test.ucdavis.edu:8000/app/search/search?q=%7Cloadjob%20scheduler__admin__search__RMD5afe10cbbfdadda93_at_1581119940_87%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now",
	"sid": "scheduler__admin__search__RMD5afe10cbbfdadda93_at_1581119940_87",
	"owner": "admin",
	"search_uri": "/servicesNS/admin/search/saved/searches/Pagerduty+page+test",
	"search_name": "Pagerduty page test",
	"results_file": "/opt/splunk/splunk/var/run/splunk/dispatch/scheduler__admin__search__RMD5afe10cbbfdadda93_at_1581119940_87/per_result_alert/tmp_0.csv.gz",
	"server_host": "splunk-test.ucdavis.edu",
	"result": {
		"_bkt": "monitoringtest~6~783A7230-D599-49B7-8719-7E7EB08CB731",
		"punct": "_",
		"_si": ["splunk-test.ucdavis.edu", "monitoringtest"],
		"sourcetype": "tcp-raw",
		"host": "128.120.32.134",
		"eventtype": "",
		"tag": "",
		"linecount": "1",
		"source": "tcp:6000",
		"_raw": "get payload",
		"_indextime": "1581119932",
		"tag::eventtype": "",
		"timestamp": "none",
		"_cd": "6:6",
		"_sourcetype": "tcp-raw",
		"_time": "1581119932",
		"splunk_server": "splunk-test.ucdavis.edu",
		"splunk_server_group": "",
		"_eventtype_color": "",
		"index": "monitoringtest",
		"_kv": "1",
		"_serial": "0"
	},
	"configuration": {"integration_key": "abc123get4me5from6pagerduty7890xyz"},
	"app": "search",
	"server_uri": "https://127.0.0.1:8089"
}
```

# Example of our POST request body
```JSON
body={
	"client": "Splunk",
	"client_url": "http://splunk-test.ucdavis.edu:8000/app/search/search?q=%7Cloadjob%20scheduler__admin__search__RMD5afe10cbbfdadda93_at_1581124980_618%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now",
	"event_action": "trigger",
	"dedup_key": "Pagerduty page test (Server: 128.120.32.134)",
	"payload": {
		"summary": "128.120.32.134 Pagerduty page test",
		"custom_details": {
			"_kv": "1",
			"_time": "1581124960",
			"_indextime": "1581124960",
			"_cd": "6:23",
			"_si": ["splunk-test.ucdavis.edu", "monitoringtest"],
			"sourcetype": "tcp-raw",
			"linecount": "1",
			"index": "monitoringtest",
			"_bkt": "monitoringtest~6~783A7230-D599-49B7-8719-7E7EB08CB731",
			"_eventtype_color": "",
			"tag::eventtype": "",
			"splunk_server": "splunk-test.ucdavis.edu",
			"_serial": "0",
			"source": "tcp:6000",
			"punct": "__",
			"_sourcetype": "tcp-raw",
			"eventtype": "",
			"splunk_server_group": "",
			"_raw": "get payload",
			"timestamp": "none",
			"host": "128.120.32.134",
			"tag": ""
		},
		"severity": "critical",
		"group": "monitoringtest",
		"source": "128.120.32.134",
		"component": "tcp-raw"
	},
	"routing_key": "abcdefghijklmnopqrstuvwxyz123456"
}
```