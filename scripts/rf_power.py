#! /usr/bin/python
# Copyright Notice:
# Copyright 2019-2020 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Tacklebox/blob/master/LICENSE.md

"""
Redfish Power Reset

File : rf_power_reset.py

Brief : This script uses the redfish_utilities module to perform a reset of the system
"""
import sys

sys.path.append('.')
sys.path.append('..')
import argparse
import redfish
import redfish_utilities

# Get the input arguments
argget = argparse.ArgumentParser(description="A tool to perform a power/reset operation of a system")
argget.add_argument("--user", "-u", type=str, required=True, help="The user name for authentication")
argget.add_argument("--password", "-p", type=str, required=True, help="The password for authentication")
argget.add_argument("--rhost", "-r", type=str, required=True, help="The address of the Redfish service (with scheme)")
argget.add_argument("--system", "-s", type=str, help="The ID of the system to reset")
argget.add_argument("--power", "-power", type=str, required=True,
                    choices=list(map(str.lower, redfish_utilities.resets.reset_types)),
                    help="The type of power/reset operation to perform")
args = argget.parse_args()

# Set up the Redfish object
redfish_obj = redfish.redfish_client(base_url=args.rhost, username=args.user, password=args.password)
redfish_obj.login(auth="session")

try:
    index = list(map(str.lower, redfish_utilities.resets.reset_types)).index(args.power)
    reset_type = redfish_utilities.resets.reset_types[index]
    print("Reset type: {}".format(reset_type))
    response = redfish_utilities.system_reset(redfish_obj, args.system, reset_type)
    response = redfish_utilities.poll_task_monitor(redfish_obj, response)
    redfish_utilities.verify_response(response)
finally:
    # Log out
    redfish_obj.logout()
