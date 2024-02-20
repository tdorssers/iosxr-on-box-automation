[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/tdorssers/iosxr-on-box-automation)

# IOS XR Automation Scripts

The scripts available on-box can now leverage [Python libraries](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/script-infrastructure-sample-templates.html), access the underlying router information to execute CLI commands, and monitor router configurations continuously. This results in setting up a seamless automation workflow by improving connectivity, access to resources, and speed of script execution. The following categories of on-box scripts are used to achieve operational simplicity:
* Configuration (Config) scripts
* Execution (Exec) scripts
* Process scripts
* Embedded Event Manager (EEM) scripts

Deploying and using EEM scripts on the router is described [here](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/711x/programmability/configuration/guide/b-programmability-cg-asr9000-711x/event-scripts.html).

## PIM DR priority EEM script

IOS XR does not support *HSRP Aware PIM*, a redundancy mechanism for the Protocol Independent Multicast (PIM) protocol to interoperate with Hot Standby Router Protocol (HSRP). It allows PIM to track HSRP state and to preserve multicast traffic upon failover in a redundant network with HSRP enabled.

This workaround uses object tracking to detect PE core isolation and uses EEM policy-maps to change the configured PIM DR priorities dynamically. The new priority value is set to the value after the word `priority` in the policy-map name. The tracked object should have an up delay configured, to give protocols time to converge once the PE is not isolated from the core anymore.

### Example usage

Required configuration:
* User and AAA configuration

```
event manager action Pim
 username <user>
 type script script-name pim.py checksum sha256 <checksum>
!
event manager policy-map Set-Priority-95
 trigger multi-event "Startup OR Isolate"
 action Pim
!
event manager policy-map Set-Priority-110
 trigger event Restore
 action Pim
!
event manager event-trigger Isolate
 type track name 1 status down
!
event manager event-trigger Restore
 type track name 1 status up
!
event manager event-trigger Startup
 type timer cron cron-entry "@reboot"
!
track 1
 type line-protocol state
  interface GigabitEthernet0/0/0/0
 !
 delay up 60
!
```

## BGP graceful maintenance EEM script

CE-PE traffic can be blackholed when a PE is isolated from the core while local prefixes are still advertised. BGP Graceful Maintenance is used as a workaround for this. When activated, the affected routes are advertised again with a reduced preference. This causes neighboring routers to choose alternative routes. You can use any of the following methods to a signal reduced route preference:
* Add GSHUT community
* Reduce LOCAL_PREF value
* Prepend AS Path

Object tracking is used to detect core isolation and EEM policy-maps are used to dynamically (de)activate BGP Graceful Maintenance. The word `activate` or `deactivate` in the policy-map name determines the new state. The tracked object should have an up delay configured, to give protocols time to converge once the router is not isolated anymore.

### Example usage

The event-triggers and tracked object from the above example are used here as well.

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

## LPTS drop monitor process script

A process script differs from an EEM script because a process script runs forever and cannot interact with the CLI as it does not have a user associated with it. This script provides alerting functionality to LPTS. The command used for measuring drop counts are `show lpts pifib hardware police location <line card>` and `show lpts pifib hardware static-police location <line card>`. If the LPTS drops exceed a certain threshold within a preset interval, a syslog message is generated. Different thresholds can be set for different flow types. The wildcard flow type, indicated by a star, is required. A threshold value must be specified for each flow type.

### Example usage

The next example runs every 60 seconds and sets a threshold of 1000 to the BGP-known flow type and a threshold of 10 for all others.

```
appmgr
 process-script Lpts-Mon
  executable lpts.py
  run-args -i 60 -f * BGP-known -t 10 1000
 !
!
script process lpts.py checksum SHA256 <checksum>
```
