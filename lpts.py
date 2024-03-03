"""
This script provides alerting functionality to LPTS on Cisco IOS-XR

If the LPTS drops exceed a certain threshold within a preset interval, a syslog
message is generated. The commands used for measuring drop counts are 'show
lpts pifib hardware [static-]police location <node>'.
Different thresholds can be set for different flow types. The wildcard flow
type, indicated by a star, is required. A threshold value must be specified for
each flow type.

Arguments:
  -i INTERVAL, --interval INTERVAL
  -f FLOWTYPE [FLOWTYPE ...], --flowtype FLOWTYPE [FLOWTYPE ...]
  -t THRESHOLD [THRESHOLD ...], --threshold THRESHOLD [THRESHOLD ...]
"""

# Author: Tim Dorssers

import re
import time
import argparse
import subprocess
from collections import defaultdict
from cisco.script_mgmt import xrlog

syslog = xrlog.getSysLogger('LPTS')
saved = defaultdict(dict)

def get_by(flow_type):
    """ Get threshold for flow type if specified """
    return next((value for key, value in zip(args.flows, args.thres)
                 if key.lower() == flow_type.lower()), 0)

def task():
    """ Run show commands and compare with previous """
    patterns = [r'(\S+)\s+\d+\s+\S+\s+\d+\s+\d+\s+\d+\s+(\d+)',
                r'(\S+)\s+\S+\s+\d+\s+\d+\s+\d+\s+(\d+)']
    commands = [['platform_show_pifib', '-z', '0x6', '-i'],
                ['platform_show_pifib', '-z', '0x7', '-i']]
    # Get hexadecimal node ID and fully qualified line card specification
    cmd = ['node_list_generation', '-c', '-f', 'LC']
    result = subprocess.run(cmd, capture_output=True, universal_newlines=True)
    nodes = re.findall(r'(0x\S+)\s(\S+)', result.stdout)
    if not nodes:
        syslog.warning('Could not get list of line cards')
    # Run show commands for each node
    for node_id, fqn in nodes:
        for cmd, pattern in zip(commands, patterns):
            # Append decimal node ID to arguments and execute command
            output = subprocess.run(
                cmd + [str(int(node_id, 16))], capture_output=True,
                universal_newlines=True).stdout
            if not re.search(pattern, output):
                syslog.error('Could not get LPTS drops for ' + fqn)
                break
            # Extract values and compare with previous
            for match in re.finditer(pattern, output):
                flow_type, drops = match.group(1), int(match.group(2))
                diff = drops - saved[node_id].get(flow_type, drops)
                threshold = get_by(flow_type) or get_by('*')
                # A negative threshold will skip this flow type
                if diff > threshold > 0:
                    syslog.info('LPTS drop threshold (%d) exceeded for flow '
                                'type %s on %s, %d drops in last %d seconds.'
                                % (threshold, flow_type, fqn, diff, meantime))
                saved[node_id][flow_type] = drops

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interval', default=60, type=int)
    parser.add_argument('-f', '--flows', nargs='+', default=['*'])
    parser.add_argument('-t', '--thres', nargs='+', default=[10], type=int)
    args = parser.parse_args()
    meantime, delay, target = 0, max(1, args.interval), time.time()
    while True:
        task()
        # Skip tasks when behind schedule
        meantime = (time.time() - target) // delay * delay + delay
        target += meantime
        time.sleep(max(0, target - time.time()))
