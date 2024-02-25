"""
This script provides alerting functionality to LPTS on Cisco IOS-XR

If the LPTS drops exceed a certain threshold within a preset interval, a syslog
message is generated. Different thresholds can be set for different flow types.
The wildcard flow type, indicated by a star, is required. A threshold value
must be specified for each flow type.

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

def get_by(flow):
    """ Get threshold for flow type if specified """
    return next((value for key, value in zip(args.flows, args.thres)
                 if key.lower() == flow.lower()), 0)

def check_nodes():
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
    for node, fqn in nodes:
        for cmd, pattern in zip(commands, patterns):
            # Append decimal node ID to arguments and execute command
            output = subprocess.run(
                cmd + [str(int(node, 16))], capture_output=True,
                universal_newlines=True).stdout
            if not re.search(pattern, output):
                syslog.error('Could not get LPTS drops for ' + fqn)
                break
            for match in re.finditer(pattern, output):
                flow, drops = match.group(1), int(match.group(2))
                if not drops:
                    continue
                diff = drops - saved[node].get(flow, drops)
                threshold = get_by(flow) or get_by('*')
                if diff > threshold > 0:
                    syslog.info('LPTS drop threshold (%d) exceeded for flow '
                                'type %s on %s, %d drops in last %d seconds.'
                                % (threshold, flow, fqn, diff, args.interval))
                saved[node][flow] = drops

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interval', default=60, type=int)
    parser.add_argument('-f', '--flows', nargs='+', default=['*'])
    parser.add_argument('-t', '--thres', nargs='+', default=[10], type=int)
    args = parser.parse_args()
    while True:
        start = time.time()
        check_nodes()
        time.sleep(max(0, args.interval - (time.time() - start)))
