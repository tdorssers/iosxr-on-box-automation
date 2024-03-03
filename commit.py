"""
EEM script implementing IOS style "archive log config" syslog notification
for IOS XR 7.3.2 or later.
"""

# Author: Tim Dorssers

import re
from cisco.script_mgmt import xrlog
from iosxr.xrcli.xrcli_helper import *
from iosxr import eem

syslog = xrlog.getSysLogger('Commit')
helper = XrcliHelper()
rc, event_dict = eem.event_reqinfo()

if __name__ == '__main__':
    # Get user and commit ID from syslog message
    m = re.search(r"user '(\S+)'.*?changes (\d+)", event_dict['msg'])
    if m:
        user = m.group(1)
        command = 'show configuration commit changes ' + m.group(2)
        result = helper.xrcli_exec(command)
        if result['status'] == 'success':
            # Config lines appear after line starting with !! until end
            m = re.match(r'.*!!.*?\n(.*)end', result['output'], re.DOTALL)
            if m:
                # One syslog message per config line
                for line in m.group(1).splitlines():
                    syslog.info('User:%s  logged command:%s' % (user, line))
        else:
            syslog.error(result['output'])
