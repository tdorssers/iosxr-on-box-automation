[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/tdorssers/iosxr-on-box-automation)

# IOS XR Automation Scripts

You can run Python scripts on routers running Cisco IOS XR software which provides [contextual support](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/script-infrastructure-sample-templates.html) using SDK libraries and standard protocols to:
* obtain operational data from the router
* set configurations and conditions
* detect events in the network and trigger an appropriate action

There are four types of on-box automation scripts that you can leverage to automate your network operations:
* Configuration ([Config](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/config-scripts.html)) scripts
* Execution ([Exec](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/exec-scripts.html)) scripts
* [Process](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/process-scripts.html) scripts
* Embedded Event Manager ([EEM](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/event-scripts.html)) scripts

## PIM DR priority EEM script

IOS XR does not support *HSRP Aware PIM*, a redundancy mechanism for the Protocol Independent Multicast (PIM) protocol to interoperate with Hot Standby Router Protocol (HSRP). It allows PIM to track HSRP state and to preserve multicast traffic upon failover in a redundant network with HSRP enabled.

Depending on the topology, different event triggers can be used. An event fired at startup is likely required in case of a collapsed core design. In a multi-layer design, tracking of the core-facing interfaces is likely required. A multiple event trigger is also possible. This workaround uses EEM policy-maps to change the configured PIM DR priorities dynamically. The new priority value is set to the value after the word *priority* in the policy-map name. The tracked object should have an up delay configured, to give protocols time to converge once the PE is not isolated from the core anymore.

### Example usage

Required configuration:
* User and AAA configuration

```
event manager action Pim
 username <user>
 type script script-name pim.py checksum sha256 <checksum>
!
event manager policy-map Set-Priority-110
 trigger event Restore
 action Pim
!
event manager event-trigger Restore
 type track name 1 status up
!
track 1
 type line-protocol state
  interface GigabitEthernet0/0/0/0
 !
 delay up 60
!
```

Policy for a collapsed core design using a timer:

```
event manager policy-map Set-Priority-95
 trigger event Startup
 action Pim
!
event manager event-trigger Startup
 type timer cron cron-entry "@reboot"
!
```

Policy for a multi-layer design using object tracking:

```
event manager policy-map Set-Priority-95
 trigger event Isolate
 action Pim
!
event manager event-trigger Isolate
 type track name 1 status down
!
```

### Details

The line `rc, event_dict = eem.event_reqinfo()` in the EEM script retrieves the event details. The `event_dict` has these common items:

| Name | Description |
| --- | --- |
| event_id | Unique number that indicates the ID for this published event. Multiple policies may be run for the same event, and each policy will have the same event_id. |
| event_pub_sec <br/> event_pub_msec | The time, in seconds and milliseconds, at which the event was published to the EEM.|
| event_name | Name of the event-trigger. |
| action_name | Name of the action. |
| policy_map_name | Name of the policy-map. |
| event_type | Type of event. |
| event_type_string | An ASCII string that represents the name of the event for this event type. |
| event_severity | The severity of the event. |

The `event_dict` for a *timer* event has these additional items:

| Name | Description |
| --- | --- |
| timer_type | Type of the timer. Can be `cron` or `watchdog`. |
| timer_time_sec <br/> timer_time_msec | Time when the timer expired. |
| timer_remain_sec <br/> timer_remain_msec | The remaining time before the next expiration. |

The `event_dict` for a *track* event has these additional items:

| Name | Description |
| --- | --- |
| track_name | Name of the tracked object. |
| track_state | State of the tracked object when the event was triggered; valid states are `up` or `down`. |

The `helper.xrcli_exec()` method returns a dictionary with these items:

| Name | Description |
| --- | --- |
| status | `success` or `error`. |
| output | The CLI output. |

## BGP graceful maintenance EEM script

CE-PE traffic can be blackholed when a PE is isolated from the core while still advertising local prefixes. BGP Graceful Maintenance is used as a workaround for this. When activated, the affected routes are advertised again with a reduced preference. This causes neighboring routers to choose alternative routes. You can use any of the following methods to a signal reduced route preference:
* Add GSHUT community
* Reduce LOCAL_PREF value
* Prepend AS Path

Object tracking is used to detect core isolation and EEM policy-maps are used to dynamically (de)activate BGP Graceful Maintenance. The word `activate` or `deactivate` in the policy-map name determines the new state. The tracked object should have an up delay configured, to give protocols time to converge once the router is not isolated anymore.

### Example usage

The event-triggers and tracked object from the above example are used here as well. It is also possible to use a multi event trigger, as shown in the `Activate` policy map below.

```
event manager action BGP
 username <user>
 type script script-name bgp.py checksum sha256 <checksum>
!
event manager policy-map Activate
 trigger multi-event "Startup OR Isolate"
 action BGP
!
event manager policy-map Deactivate
 trigger event Restore
 action BGP
!
```

## Commit syslog EEM script

This EEM script implements the IOS style `archive log config` syslog notification for IOS XR. The syslog event trigger is used to detect a commit. A syslog message is generated for each committed configuration line.

### Example usage

```
event manager action Log-Config
 username <user>
 type script script-name commit.py checksum sha256 <checksum>
!
event manager policy-map Archive
 trigger event Commit
 action Log-Config
!
event manager event-trigger Commit
 type syslog pattern "%MGBL-CONFIG-6-DB_COMMIT : Configuration committed by user"
!
```

### Details

The `event_dict` for a *syslog* event has these additional items:

| Name | Description |
| --- | --- |
| msg_count | Number of times the pattern matched before the event was triggered. |
| msg | The last syslog message that matches the pattern. |
| priority | The message priority. |

## LPTS drop monitor process script

This script provides alerting functionality to LPTS. If the LPTS drops exceed a certain threshold within a preset interval, a syslog message is generated. Different thresholds can be set for different flow types. The wildcard flow type, indicated by a star, is required. A threshold value must be specified for each flow type.

A process script differs from an EEM script because a process script runs forever and cannot interact with the CLI as it does not have a user associated with it. Deploying and using process scripts on the router is described [here](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/process-scripts.html).

The commands used for measuring drop counts are `show lpts pifib hardware police location <line card>` and `show lpts pifib hardware static-police location <line card>`. The `describe` command can be used to find the process to spawn like this:

```
RP/0/RSP0/CPU0:ios#describe show lpts pifib hardware police location 0/0/CPU0
The command is defined in gcp_pifib_cmds.parser


User needs ALL of the following taskids:

        lpts (READ) 

It will take the following actions:
Sun Feb 25 14:02:20.937 CET
  Spawn the process:
    platform_show_pifib "-z" "0x6" "-i" "33312" 
```

### Example usage

The next example sets an interval of 60 seconds and a threshold of 1000 packets to the BGP-known flow type and a threshold of 10 packets for all others.

```
appmgr
 process-script Lpts-Mon
  executable lpts.py
  run-args -i 60 -f * BGP-known -t 10 1000
 !
!
script process lpts.py checksum SHA256 <checksum>
```

### Example output

```
RP/0/RSP0/CPU0:Feb 25 13:59:37.362 CET: scripting_python3[67253]: %OS-SCRIPT_LOG-6-INFO : Script-LPTS: LPTS drop threshold (10) exceeded for flow type PIM-mcast-known on 0/1/CPU0, 120318 drops in last 60 seconds.
RP/0/RSP0/CPU0:Feb 25 13:59:37.945 CET: scripting_python3[67253]: %OS-SCRIPT_LOG-6-INFO : Script-LPTS: LPTS drop threshold (10) exceeded for flow type PUNT_MAC_SECURE_VIOLATION on 0/1/CPU0, 2204316 drops in last 60 seconds. 
```

## Storm control drop monitor process script

This script will monitor the drop count over a predefined time interval. If the drops exceed a certain threshold value then a syslog message will be generated. The command used for measuring drop counts is 'show l2vpn bridge-domain detail'. The threshold argument takes either a single value for BUM traffic or a list of three values to specify broadcast, multicast and unknown unicast respectively. If you don't specify a value for the thresholds the default will be 100p.

### Example usage

The next example sets an interval of 60 seconds and all thresholds to 10 packets.

```
appmgr
 process-script Storm-Ctrl-Mon
  executable storm.py
  run-args -i 60 -t 10
 !
!
script process storm.py checksum SHA256 <checksum>
```

### Example output

```
RP/0/RSP0/CPU0:Feb 25 14:00:28.782 CET: scripting_python3[66324]: %OS-SCRIPT_LOG-6-INFO : Script-Storm: Multicast traffic drop exceeded threshold 10p/60s on BG:EVC_00010_BD Bundle-Ether10100.10 Exact value: 60 
RP/0/RSP0/CPU0:Feb 25 14:00:28.805 CET: scripting_python3[66324]: %OS-SCRIPT_LOG-6-INFO : Script-Storm: Multicast traffic drop exceeded threshold 10p/60s on BG:EVC_00010_BD neighbor: 10.254.255.2, ID: 36885:10 Exact value: 19 
RP/0/RSP0/CPU0:Feb 25 14:01:28.795 CET: scripting_python3[66324]: %OS-SCRIPT_LOG-6-INFO : Script-Storm: Multicast traffic drop exceeded threshold 10p/60s on BG:EVC_00010_BD Bundle-Ether10100.10 Exact value: 11 
RP/0/RSP0/CPU0:Feb 25 14:01:28.818 CET: scripting_python3[66324]: %OS-SCRIPT_LOG-6-INFO : Script-Storm: Multicast traffic drop is below threshold 10p/60s on BG:EVC_00010_BD neighbor: 10.254.255.2, ID: 36885:10 
RP/0/RSP0/CPU0:Feb 25 14:02:28.817 CET: scripting_python3[66324]: %OS-SCRIPT_LOG-6-INFO : Script-Storm: Multicast traffic drop is below threshold 10p/60s on BG:EVC_00010_BD Bundle-Ether10100.10
```