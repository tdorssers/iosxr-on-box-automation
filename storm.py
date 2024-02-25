"""
This script will monitor the drop count over a predefined time interval.

If the drops exceed a certain threshold value then a syslog message will
be generated. The command used for measuring drop counts is 'show l2vpn
bridge-domain detail'.
The threshold argument takes either a single value for BUM traffic or a list of
three values to specify broadcast, multicast and unknown unicast respectively.
If you don't specify a value for the thresholds the default will be 100p.

Arguments:
  -i INTERVAL, --interval INTERVAL
  -t THRESHOLD [THRESHOLD ...], --threshold THRESHOLD [THRESHOLD ...]
"""

# Author: Tim Dorssers

import re
import time
import argparse
import subprocess
from collections import defaultdict
from cisco.script_mgmt import xrlog

syslog = xrlog.getSysLogger('Storm')
saved = defaultdict(dict)

def log_drop(drop_type, bd_name, intf, diff=0):
    """ Format log message """
    msg = ['Broadcast', 'Multicast', 'Unknown unicast'][drop_type] + ' traffic'
    msg += ' drop exceeded threshold' if diff else ' drop is below threshold'
    msg += ' %dp/%ds on %s ' % (threshold[drop_type], args.interval, bd_name)
    msg += 'neighbor: %s, ID: %s' % intf if isinstance(intf, tuple) else intf
    syslog.info(msg + ' Exact value: %d' % diff if diff else msg)

def check_drop(bd_name, intf, drop_type, drop_val):
    """ Compare with previous values """
    old_val, old_diff = saved[intf].get(drop_type, (drop_val, 0))
    diff = drop_val - old_val
    saved[intf][drop_type] = (drop_val, diff)
    if diff > threshold[drop_type]:
        log_drop(drop_type, bd_name, intf, diff)
    elif old_diff > threshold[drop_type]:
        log_drop(drop_type, bd_name, intf)

def monitor():
    """ Run show command """
    bd_name, intf = '', None
    # get output line by line as soon as subprocess flushes its stdout buffer
    with subprocess.Popen(['l2vpn_show', '-d', '0x9'], stdout=subprocess.PIPE,
                          universal_newlines=True) as proc:
        for line in proc.stdout:
            # find bridge domain and bridge name
            m = re.match(r'Bridge group: (.*?), bridge-domain: (.*?),', line)
            if m:
                bd_name = ':'.join(m.group(1, 2))
                intf = None
            # find the AC lines
            m = re.match(r'\s+AC: (.*?), state is up', line)
            if m:
                intf = m.group(1)
            # find the PW lines
            m = re.match(r'\s+PW: neighbor (.*?), PW ID (.*?),', line)
            if m:
                intf = m.group(1, 2)
            # find dropped packets
            if intf:
                m = re.match(r'\s+packets: broadcast (\d+), multicast (\d+),'
                             r' unknown unicast (\d+)', line)
                if m:
                    for drop_type, drop_val in enumerate(m.group(1, 2, 3)):
                        check_drop(bd_name, intf, drop_type, int(drop_val))
                    intf = None
    if not bd_name:
        syslog.error('Could not get bridge-domain details')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interval', default=60, type=int)
    parser.add_argument('-t', '--thres', nargs='+', default=[100], type=int)
    args = parser.parse_args()
    threshold = args.thres if len(args.thres) == 3 else args.thres[:1] * 3
    while True:
        start = time.time()
        monitor()
        time.sleep(max(0, args.interval - (time.time() - start)))
