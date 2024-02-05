# IOS XR Automation Scripts

## PIM

The PIM implementation of IOS XR is not HSRP aware. This workaround uses
object tracking to detect core isolation and EEM policy-maps to change the
configured DR priorities dynamically. The new priority value is extracted from
the policy-map name. The tracked object should have an up delay configured,
to give protocols time to converge once the routers is not isolated anymore.

Required configuration:
User and AAA configuration

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
