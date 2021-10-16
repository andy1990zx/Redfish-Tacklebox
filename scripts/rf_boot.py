#! /usr/bin/python
# Copyright Notice:
# Copyright 2019-2020 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Tacklebox/blob/master/LICENSE.md

"""
Redfish Boot

File : rf_boot.py

Brief : This script uses the redfish_utilities module to manage a boot function of a system
"""
import sys

sys.path.append('.')
sys.path.append('..')
import argparse
import redfish
import redfish_utilities

# Get the input arguments
argget = argparse.ArgumentParser(description="A tool to perform a boot function of a system")
argget.add_argument("--user", "-u", type=str, required=True, help="The user name for authentication")
argget.add_argument("--password", "-p", type=str, required=True, help="The password for authentication")
argget.add_argument("--rhost", "-r", type=str, required=True, help="The address of the Redfish service (with scheme)")
argget.add_argument("--system", "-s", type=str, help="The ID of the system to set")
argget.add_argument("--target", "-t", type=str, choices=redfish_utilities.systems.ov_target_values,
                    help="The target boot device; if not provided the tool will display the current boot settings")
# argget.add_argument("--uefi", "-uefi", type=str,
#                     help="If target is 'UefiTarget', the UEFI Device Path of the device to boot.  If target is "
#                          "'UefiBootNext', the UEFI Boot Option string of the device to boot.")
args = argget.parse_args()

# Set up the Redfish object
redfish_obj = redfish.redfish_client(base_url=args.rhost, username=args.user, password=args.password)
redfish_obj.login(auth="session")

try:
    if args.target is None:
        # Target not specified; just get the settings and display them
        boot1, boot2 = redfish_utilities.get_system_boot(redfish_obj, args.system)
        boot = boot1 if boot2 is None else boot2
        redfish_utilities.print_system_boot(boot)
        # print_system_boot_options
        print('Boot Options:')
        boot_options = redfish_obj.get(boot1['BootOptions']['@odata.id'])
        if 'Members' not in boot_options.dict:
            print('  No boot options available.')
        for index, boot_option in enumerate(boot_options.dict['Members']):
            boot_option_context = redfish_obj.get(boot_option['@odata.id'])
            print('  Boot Option #{}:'.format(index))
            element_to_display = ['BootOptionReference', 'DisplayName', 'Alias', 'BootOptionEnabled', 'UefiDevicePath']
            for element in element_to_display:
                if element in boot_option_context.dict:
                    print('    {:20s}: {}'.format(element, boot_option_context.dict[element]))
    else:
        # Build and send the boot request based on the arguments given
        uefi_target = None
        boot_next = None
        boot_mode = "Once"
        # if args.target == "UefiTarget":
        #     uefi_target = args.uefi
        # if args.target == "UefiBootNext":
        #     boot_next = args.uefi
        if args.target == "None":
            print("Disabling one time boot...")
            boot_mode = "Disabled"
        else:
            print("Setting a one time boot for {}...".format(args.target))
        redfish_utilities.set_system_boot(redfish_obj, args.system, args.target, boot_mode, None, uefi_target,
                                          boot_next)
    print('Operation successes')
finally:
    # Log out
    redfish_obj.logout()
