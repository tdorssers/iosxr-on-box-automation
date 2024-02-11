"""
This EEM script for IOS XR 7.5.1 or later should be used with object tracking
to detect core isolation and uses EEM policy-maps to dynamically change the
configured DR priorities. The new priority value is taken from the policy-map
name. The tracked object should have an up delay configured, to give protocols
time to converge once the router is not isolated anymore.
"""

# Author: Tim Dorssers

import re
from cisco.script_mgmt import xrlog
from iosxr.xrcli.xrcli_helper import *
from iosxr import eem

syslog = xrlog.getSysLogger('PIM')
helper = XrcliHelper()
rc, event_dict = eem.event_reqinfo()

def conf_dr_prio(new):
    """ Get and set PIM DR priority configuration lines for all VRFs """
    command = 'show running-config formal router pim | include dr-priority'
    result = helper.xrcli_exec(command)
    if result['status'] == 'error':
        syslog.error(result['output'])
        return
    # Filter configuration lines from the output and split the priority
    matches = re.findall(r'(router.*?)(\d+)$', result['output'], re.M)
    # Create new configuration lines if the current priority is different
    config = [line + new for line, old in matches if old != new]
    if not config:
        syslog.info('PIM DR priorities already set')
        return
    syslog.info('Setting PIM DR priorities to %s' % new)
    result = helper.xr_apply_config_string('\n'.join(config))
    if result['status'] == 'success':
        syslog.info('Commit success')
    else:
        syslog.error(result['output'])

if __name__ == '__main__':
    syslog.info(event_dict['event_name'] + ' event occurred')
    # Set priority to the value after the word priority in the policy-map name
    match = re.search(r'prio.*?(\d+)', event_dict['policy_map_name'], re.I)
    conf_dr_prio(match.group(1) if match else '100')
