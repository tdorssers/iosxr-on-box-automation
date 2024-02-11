"""
This EEM script for IOS XR 7.5.1 or later should be used with object tracking
to detect core isolation and uses EEM policy-maps to dynamically (de)activate
BGP Graceful Maintenance. The new state is taken from the policy-map name. The
tracked object should have an up delay configured, to give protocols time to
converge once the router is not isolated anymore.
"""

# Author: Tim Dorssers

import re
from cisco.script_mgmt import xrlog
from iosxr.xrcli.xrcli_helper import *
from iosxr import eem

syslog = xrlog.getSysLogger('BGP')
helper = XrcliHelper()
rc, event_dict = eem.event_reqinfo()

def conf_gr_maint(state):
    """ Enable or disable BGP Graceful Maintenance for all neighbors """
    command = 'show running formal router bgp | include graceful-maintenance'
    result = helper.xrcli_exec(command)
    if result['status'] == 'error':
        syslog.error(result['output'])
        return
	# Get BGP AS from the output
    match = re.search(r'router bgp (\d+)', result['output'])
    if not match:
        syslog.info('Could not get BGP AS')
        return
    if 'all-neighbors' in result['output'] and state:
        syslog.info('BGP Graceful Maintenance (All Neighbors) already active')
        return
    if state:
        syslog.info('Activating BGP Graceful Maintenance for all neighbors')
        config = 'router bgp %s graceful-maintenance activate all-neighbors'
    else:
        syslog.info('Deactivating BGP Graceful Maintenance')
        config = 'no router bgp %s graceful-maintenance activate'
    result = helper.xr_apply_config_string(config % match.group(1))
    if result['status'] == 'success':
        syslog.info('Commit success')
    else:
        syslog.error(result['output'])

if __name__ == '__main__':
    syslog.info(event_dict['event_name'] + ' event occurred')
	# The word (de)activate in the policy-map name determines state
    match = re.search(r'(?<!de)activate', event_dict['policy_map_name'], re.I)
    conf_gr_maint(bool(match))
