#! /usr/bin/python
# Copyright Notice:
# Copyright 2019-2021 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Tacklebox/blob/master/LICENSE.md

"""
Systems Module

File : systems.py

Brief : This file contains the definitions and functionalities for interacting
        with the systems collection for a given Redfish service
"""

import warnings
from .messages import verify_response
from .resets import reset_types
from .root import get_root_level_resource


class RedfishSystemNotFoundError(Exception):
    """
    Raised when a matching system cannot be found
    """
    pass


class RedfishSystemResetNotFoundError(Exception):
    """
    Raised when the reset action cannot be found
    """
    pass


class RedfishSystemBootNotFoundError(Exception):
    """
    Raised when the boot object cannot be found
    """
    pass


class RedfishSystemBiosNotFoundError(Exception):
    """
    Raised when the BIOS resource cannot be found
    """
    pass


class RedfishSystemBiosInvalidSettingsError(Exception):
    """
    Raised when the BIOS resource contains a settings object, but it's not rendered properly
    """
    pass


class RedfishVirtualMediaNotFoundError(Exception):
    """
    Raised when a system does not have any virtual media available
    """
    pass


class RedfishNoAcceptableVirtualMediaError(Exception):
    """
    Raised when a system does not have virtual media available that meets criteria
    """
    pass


class RedfishNoResourceError(Exception):
    """
    Raise can't find resource error
    """
    pass


class RedfishCommonError(Exception):
    """
    Raise common error
    """
    pass


ov_target_values = ["None", "Pxe", "Usb", "Hdd", "BiosSetup"]


def get_system_ids(context):
    """
    Finds the system collection and returns all of the member's identifiers

    Args:
        context: The Redfish client object with an open session

    Returns:
        A list of identifiers of the members of the system collection
    """

    # Get the service root to find the system collection
    service_root = context.get("/redfish/v1/")
    if "Systems" not in service_root.dict:
        # No system collection
        raise RedfishSystemNotFoundError("Service does not contain a system collection")

    # Get the system collection and iterate through its collection
    avail_systems = []
    system_col = context.get(service_root.dict["Systems"]["@odata.id"])
    while True:
        for system_member in system_col.dict["Members"]:
            avail_systems.append(system_member["@odata.id"].strip("/").split("/")[-1])
        if "Members@odata.nextLink" not in system_col.dict:
            break
        system_col = context.get(system_col.dict["Members@odata.nextLink"])
    return avail_systems


def get_system(context, system_id=None):
    """
    Finds a system matching the given identifier and returns its resource

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        The system resource
    """

    system_uri_pattern = "/redfish/v1/Systems/{}"
    avail_systems = None

    # If given an identifier, get the system directly
    if system_id is not None:
        system = context.get(system_uri_pattern.format(system_id))
    # No identifier given; see if there's exactly one member
    else:
        avail_systems = get_system_ids(context)
        if len(avail_systems) == 1:
            system = context.get(system_uri_pattern.format(avail_systems[0]))
        else:
            raise RedfishSystemNotFoundError(
                "Service does not contain exactly one system; a target system needs to be specified: {}".format(
                    ", ".join(avail_systems)))

    # Check the response and return the system if the response is good
    try:
        verify_response(system)
    except:
        if avail_systems is None:
            avail_systems = get_system_ids(context)
        raise RedfishSystemNotFoundError(
            "Service does not contain a system called {}; valid systems: {}".format(system_id,
                                                                                    ", ".join(avail_systems))) from None
    return system


def get_system_boot(context, system_id=None):
    """
    Finds a system matching the given ID and returns its Boot objects

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        Two boot object from the given system
        0: System boot
        1: if System boot support '@Redfish.Settings', return '@Redfish.Settings', eles None
    """

    system1 = get_system(context, system_id)
    system2 = None
    if '@Redfish.Settings' in system1.dict:
        system2 = context.get(system1.dict["@Redfish.Settings"]['SettingsObject']['@odata.id'])
    if "Boot" not in system1.dict:
        raise RedfishSystemBootNotFoundError("System '{}' does not contain the boot object".format(system1.dict["Id"]))

    if system2 is None:
        return system1.dict["Boot"], None
    else:
        return system1.dict["Boot"], system2.dict["Boot"]


def set_system_boot(context, system_id=None, ov_target=None, ov_enabled=None, ov_mode=None, ov_uefi_target=None,
                    ov_boot_next=None):
    """
    Finds a system matching the given ID and updates its Boot object

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system
        ov_target: The override target (BootSourceOverrideTarget)
        ov_enabled: The override enabled setting (BootSourceOverrideEnabled)
        ov_mode: The override mode setting (BootSourceOverrideMode)
        ov_uefi_target: The UEFI target for override (UefiTargetBootSourceOverride)
        ov_boot_next: The UEFI boot next for override (BootNext)

    Returns:
        The response of the PATCH
    """
    global ov_target_values
    # Check that the values themselves are supported by the schema
    if ov_target is not None:
        if ov_target not in ov_target_values:
            raise ValueError(
                "{} is not an allowable override target ({})".format(ov_target, ", ".join(ov_target_values)))
    ov_enabled_values = ["Disabled", "Once", "Continuous"]
    if ov_enabled is not None:
        if ov_enabled not in ov_enabled_values:
            raise ValueError(
                "{} is not an allowable override enabled ({})".format(ov_enabled, ", ".join(ov_enabled_values)))
    ov_mode_values = ["Legacy", "UEFI"]
    if ov_mode is not None:
        if ov_mode not in ov_mode_values:
            raise ValueError("{} is not an allowable override mode ({})".format(ov_mode, ", ".join(ov_mode_values)))

    # Locate the system
    system = get_system(context, system_id)
    if '@Redfish.Settings' in system.dict:
        system = context.get(system.dict["@Redfish.Settings"]['SettingsObject']['@odata.id'])

    # Build the payload
    payload = {"Boot": {}}
    if ov_target is not None:
        payload["Boot"]["BootSourceOverrideTarget"] = ov_target
    if ov_enabled is not None:
        payload["Boot"]["BootSourceOverrideEnabled"] = ov_enabled
    if ov_mode is not None:
        payload["Boot"]["BootSourceOverrideMode"] = ov_mode
    if ov_uefi_target is not None:
        payload["Boot"]["UefiTargetBootSourceOverride"] = ov_uefi_target
    if ov_boot_next is not None:
        payload["Boot"]["BootNext"] = ov_boot_next

    # Update the system
    headers = None
    etag = system.getheader("ETag")
    if etag is not None:
        headers = {"If-Match": etag}
    response = context.patch(system.dict["@odata.id"], body=payload, headers=headers)
    verify_response(response)
    return response


def print_system_boot(boot):
    """
    Prints the contents of a Boot object

    Args:
        boot: The Boot object to print
    """

    print("")

    print("Boot Override Settings:")
    boot_properties = ["BootSourceOverrideTarget", "BootSourceOverrideEnabled"]
    boot_strings = ["Target", "Enabled"]
    for index, boot_property in enumerate(boot_properties):
        if boot_property in boot:
            out_string = '  {:7s} ({:25s}) : {}'.format(boot_strings[index], boot_properties[index],
                                                        boot[boot_property])
            allow_string = ""
            # if boot_property + "@Redfish.AllowableValues" in boot:
            #     allow_string = "; Allowable Values: {}".format(
            #         ", ".join(boot[boot_property + "@Redfish.AllowableValues"]))
            print(out_string + allow_string)

    print("")


def get_system_reset_info(context, system_id=None):
    """
    Finds a system matching the given ID and returns its reset info

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        The URI of the Reset action
        A list of parameter requirements from the Action Info
    """

    system = get_system(context, system_id)

    # Check that there is a Reset action
    if "Actions" not in system.dict:
        raise RedfishSystemResetNotFoundError("System '{}' does not support the reset action".format(system.dict["Id"]))
    if "#ComputerSystem.Reset" not in system.dict["Actions"]:
        raise RedfishSystemResetNotFoundError("System '{}' does not support the reset action".format(system.dict["Id"]))

    # Extract the info about the Reset action
    reset_action = system.dict["Actions"]["#ComputerSystem.Reset"]
    reset_uri = reset_action["target"]

    if "@Redfish.ActionInfo" not in reset_action:
        # No action info; need to build this manually based on other annotations

        # Default parameter requirements
        reset_parameters = [
            {
                "Name": "ResetType",
                "Required": False,
                "DataType": "String",
                "AllowableValues": reset_types
            }
        ]

        # Get the AllowableValues from annotations
        for param in reset_parameters:
            if param["Name"] + "@Redfish.AllowableValues" in reset_action:
                param["AllowableValues"] = reset_action[param["Name"] + "@Redfish.AllowableValues"]
    else:
        # Get the action info and its parameter listing
        action_info = context.get(reset_action["@Redfish.ActionInfo"])
        reset_parameters = action_info.dict["Parameters"]

    return reset_uri, reset_parameters


def system_reset(context, system_id=None, reset_type=None):
    """
    Finds a system matching the given ID and performs a reset

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system
        reset_type: The type of reset to perform; if None, perform one of the common resets

    Returns:
        The response of the action
    """

    # Check that the values themselves are supported by the schema
    reset_type_values = reset_types
    if reset_type is not None:
        if reset_type not in reset_type_values:
            raise ValueError("{} is not an allowable reset type ({})".format(reset_type, ", ".join(reset_type_values)))

    # Locate the reset action
    reset_uri, reset_parameters = get_system_reset_info(context, system_id)

    # Build the payload
    if reset_type is None:
        for param in reset_parameters:
            if param["Name"] == "ResetType":
                if "GracefulRestart" in param["AllowableValues"]:
                    reset_type = "GracefulRestart"
                elif "ForceRestart" in param["AllowableValues"]:
                    reset_type = "ForceRestart"
                elif "PowerCycle" in param["AllowableValues"]:
                    reset_type = "PowerCycle"

    payload = {}
    if reset_type is not None:
        payload["ResetType"] = reset_type

    # Reset the system
    response = context.post(reset_uri, body=payload)
    verify_response(response)
    return response


def get_virtual_media(context, system_id=None):
    """
    Finds the system matching the given ID and gets its virtual media

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        An array of dictionaries of the virtual media instances
    """

    # Get the virtual media collection
    virtual_media_collection = get_virtual_media_collection(context, system_id=system_id)

    # Iterate through the members and pull out each of the instances
    virtual_media_list = []
    for member in virtual_media_collection.dict["Members"]:
        virtual_media = context.get(member["@odata.id"])
        virtual_media_list.append(virtual_media.dict)
    return virtual_media_list


def print_virtual_media(virtual_media_list):
    """
    Prints the virtual media list into a table

    Args:
        virtual_media_list: The virtual media list to print
    """

    virtual_media_line_format = "  {:20s} | {}: {}"
    virtual_media_properties = ["Image", "MediaTypes", "ConnectedVia", "Inserted", "WriteProtected"]
    print("")
    for virtual_media in virtual_media_list:
        print(virtual_media_line_format.format(virtual_media["Id"], "ImageName", virtual_media.get("ImageName", "")))
        for virtual_media_property in virtual_media_properties:
            if virtual_media_property in virtual_media:
                prop_val = virtual_media[virtual_media_property]
                if isinstance(prop_val, list):
                    prop_val = ", ".join(prop_val)
                print(virtual_media_line_format.format("", virtual_media_property, prop_val))
        print("")


def insert_virtual_media(context, image, system_id=None, media_id=None, media_types=None, inserted=None,
                         write_protected=None):
    """
    Finds the system matching the given ID and inserts virtual media

    Args:
        context: The Redfish client object with an open session
        image: The URI of the media to insert
        system_id: The system to locate; if None, perform on the only system
        media_id: The virtual media instance to insert; if None, perform on an appropriate instance
        media_types: A list of acceptable media types
        inserted: Indicates if the media is to be marked as inserted for the system
        write_protected: Indicates if the media is to be marked as write-protected for the system

    Returns:
        The response of the insert operation
    """

    # Set up acceptable media types based on the image URI if not specified
    if media_types is None:
        if image.lower().endswith(".iso"):
            media_types = ["CD", "DVD"]
        elif image.lower().endswith(".img"):
            media_types = ["USBStick"]
        elif image.lower().endswith(".bin"):
            media_types = ["USBStick"]

    # Get the virtual media collection
    virtual_media_collection = get_virtual_media_collection(context, system_id=system_id)

    # Scan the virtual media for an appropriate slot
    match = False
    for member in virtual_media_collection.dict["Members"]:
        media = context.get(member["@odata.id"])
        if media.dict["Image"] is not None:
            # In use; move on
            continue

        # Check for a match
        if media_id is not None:
            if media.dict["Id"] == media_id:
                # Identifier match
                match = True
        else:
            if media_types is None:
                # No preferred media type; automatic match
                match = True
            else:
                # Check if the preferred media type is in the reported list
                for media_type in media_types:
                    if media_type in media.dict["MediaTypes"]:
                        # Acceptable media type found
                        match = True

        # If a match was found, attempt to insert the media
        if match:
            payload = {
                "Image": image
            }
            if inserted:
                payload["Inserted"] = inserted
            if write_protected:
                payload["WriteProtected"] = write_protected
            try:
                # Preference for using the InsertMedia action
                response = context.post(media.dict["Actions"]["#VirtualMedia.InsertMedia"]["target"], body=payload)
            except:
                # Fallback to PATCH method
                if "Inserted" not in payload:
                    payload["Inserted"] = True
                headers = None
                etag = media.getheader("ETag")
                if etag is not None:
                    headers = {"If-Match": etag}
                response = context.patch(media.dict["@odata.id"], body=payload, headers=headers)
            verify_response(response)
            return response

    # No matches found
    if media_id is not None:
        reason = "'{}' not found or is already in use".format(media_id)
    elif media_types is not None:
        reason = "No available slots of types {}".format(", ".join(media_types))
    else:
        reason = "No available slots"
    raise RedfishNoAcceptableVirtualMediaError("No acceptable virtual media: {}".format(reason))


def eject_virtual_media(context, media_id, system_id=None):
    """
    Finds the system matching the given ID and ejects virtual media

    Args:
        context: The Redfish client object with an open session
        media_id: The virtual media instance to eject
        system_id: The system to locate; if None, perform on the only system

    Returns:
        The response of the eject operation
    """

    # Get the virtual media collection
    virtual_media_collection = get_virtual_media_collection(context, system_id=system_id)

    # Scan the virtual media for the selected slot
    for member in virtual_media_collection.dict["Members"]:
        media = context.get(member["@odata.id"])
        if media.dict["Id"] == media_id:
            # Found the selected slot; eject it
            try:
                # Preference for using the EjectMedia action
                response = context.post(media.dict["Actions"]["#VirtualMedia.EjectMedia"]["target"], body={})
            except:
                # Fallback to PATCH method
                payload = {
                    "Image": None,
                    "Inserted": False
                }
                headers = None
                etag = media.getheader("ETag")
                if etag is not None:
                    headers = {"If-Match": etag}
                response = context.patch(media.dict["@odata.id"], body=payload, headers=headers)
            verify_response(response)
            return response

    # No matches found
    raise RedfishNoAcceptableVirtualMediaError("No acceptable virtual media: '{}' not found".format(media_id))


def get_virtual_media_collection(context, system_id=None):
    """
    Finds the system matching the given ID and gets its virtual media collection

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        The virtual media collection
    """

    # Locate the system
    system = get_system(context, system_id)

    # Check if there is a VirtualMediaCollection; if not, try the older location in the Manager resource
    virtual_media_uri = None
    if "VirtualMedia" in system.dict:
        virtual_media_uri = system.dict["VirtualMedia"]["@odata.id"]
    else:
        if "Links" in system.dict:
            if "ManagedBy" in system.dict["Links"]:
                for manager in system.dict["Links"]["ManagedBy"]:
                    manager_resp = context.get(manager["@odata.id"])
                    if "VirtualMedia" in manager_resp.dict:
                        # Get the first manager that contains virtual media
                        virtual_media_uri = manager_resp.dict["VirtualMedia"]["@odata.id"]
                        break
    if virtual_media_uri is None:
        raise RedfishVirtualMediaNotFoundError("System '{}' does not support virtual media".format(system.dict["Id"]))

    # Get the VirtualMediaCollection
    return context.get(virtual_media_uri)


def get_system_bios(context, system_id=None, workaround=False):
    """
    Finds a system matching the given ID and gets the BIOS settings

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system
        workaround: Indicates if workarounds should be attempted for non-conformant services

    Returns:
        A dictionary of the current BIOS attributes
        A dictionary of the BIOS attributes on the next reset
    """

    # Locate the system
    system = get_system(context, system_id)

    # Get the Bios resource
    if "Bios" not in system.dict:
        raise RedfishSystemBiosNotFoundError("System '{}' does not support representing BIOS".format(system.dict["Id"]))
    bios = context.get(system.dict["Bios"]["@odata.id"])
    current_settings = bios.dict["Attributes"]
    future_settings = bios.dict["Attributes"]

    # Get the Settings object if present
    if "@Redfish.Settings" in bios.dict:
        try:
            bios_settings = get_system_bios_settings(context, bios, system.dict["Id"], workaround)
            future_settings = bios_settings.dict["Attributes"]
        except:
            if workaround:
                warnings.warn(
                    "System '{}' BIOS resource contains the settings term, but no 'SettingsObject'.  Contact your "
                    "vendor.  Workarounds exhausted for reading the settings data and falling back on using the "
                    "active attributes.".format(
                        system_id))
            else:
                raise

    return current_settings, future_settings


def set_system_bios(context, settings, system_id=None, workaround=False):
    """
    Finds a system matching the given ID and sets the BIOS settings

    Args:
        context: The Redfish client object with an open session
        settings: The settings to apply to the system
        system_id: The system to locate; if None, perform on the only system
        workaround: Indicates if workarounds should be attempted for non-conformant services

    Returns:
        The response of the PATCH
    """

    # Locate the system
    system = get_system(context, system_id)

    # Get the BIOS resource and determine if the settings need to be applied to the resource itself or the settings
    # object
    if "Bios" not in system.dict:
        raise RedfishSystemBiosNotFoundError("System '{}' does not support representing BIOS".format(system.dict["Id"]))
    bios_uri = system.dict["Bios"]["@odata.id"]
    bios = context.get(bios_uri)
    etag = bios.getheader("ETag")
    if "@Redfish.Settings" in bios.dict:
        bios_settings = get_system_bios_settings(context, bios, system.dict["Id"], workaround)
        bios_uri = bios_settings.dict["@odata.id"]
        etag = bios_settings.getheader("ETag")

    # Update the settings
    payload = {"Attributes": settings}
    headers = None
    if etag is not None:
        headers = {"If-Match": etag}
    response = context.patch(bios_uri, body=payload, headers=headers)
    verify_response(response)
    return response


def get_system_bios_settings(context, bios, system_id, workaround):
    """
    Gets the settings resource for BIOS and applies workarounds if needed

    Args:
        context: The Redfish client object with an open session
        bios: The BIOS resource
        system_id: The system identifier
        workaround: Indicates if workarounds should be attempted for non-conformant services

    Returns:
        The Settings resource for BIOS
    """

    if "SettingsObject" in bios.dict["@Redfish.Settings"]:
        bios_settings = context.get(bios.dict["@Redfish.Settings"]["SettingsObject"]["@odata.id"])
    else:
        if workaround:
            warnings.warn(
                "System '{}' BIOS resource contains the settings term, but no 'SettingsObject'.  Contact your vendor. "
                " Attempting workarounds...".format(
                    system_id))
            settings_uris = ["Settings", "SD"]
            for setting_ext in settings_uris:
                bios_settings = context.get(bios.dict["@odata.id"] + "/" + setting_ext)
                if bios_settings.status == 200:
                    break
            try:
                verify_response(bios_settings)
            except:
                raise RedfishSystemBiosInvalidSettingsError(
                    "System '{}' BIOS resource contains the settings term, but no 'SettingsObject'.  Workarounds "
                    "exhausted.  Contact your vendor.".format(
                        system_id)) from None
        else:
            raise RedfishSystemBiosInvalidSettingsError(
                "System '{}' BIOS resource contains the settings term, but no 'SettingsObject'.  Contact your vendor, "
                "or retry with the 'workaround' flag.".format(
                    system_id))

    return bios_settings


def print_system_bios(current_settings, future_settings):
    """
    Prints the system BIOS settings into a table

    Args:
        current_settings: A dictionary of the current BIOS attributes
        future_settings: A dictionary of the BIOS attributes on the next reset
    """

    print("")
    print("BIOS Settings:")

    bios_line_format = "  {:30s} | {:30s} | {:30s}"
    print(bios_line_format.format("Attribute Name", "Current Setting", "Future Setting"))
    for attribute, value in sorted(current_settings.items()):
        if attribute in future_settings:
            print(bios_line_format.format(attribute, str(current_settings[attribute]), str(future_settings[attribute])))
        else:
            print(
                bios_line_format.format(attribute, str(current_settings[attribute]), str(current_settings[attribute])))

    print("")


def get_system_bios_info(context, system_id=None, language=None, attribute=None):
    """
    Finds a system matching the given ID and gets the BIOS settings info matching the given attribute

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system
        language: The language to get; if None, use en-US
        attribute: The attribute to get; if None, get all

    Returns:
        A list contains all attributes asked
    """

    # Locate the system
    system = get_root_level_resource(context, 'Systems', system_id)

    # Get the Bios resource
    if "Bios" not in system.dict:
        raise RedfishNoResourceError("System '{}' does not support representing BIOS".format(system.dict["Id"]))
    bios = context.get(system.dict["Bios"]["@odata.id"])

    if "AttributeRegistry" not in bios.dict:
        raise RedfishNoResourceError("'{}' does not support representing AttributeRegistry".format(bios.dict["Id"]))

    # Get AttributeRegistry from root.Registries
    bios_registry_id = bios.dict["AttributeRegistry"]
    bios_registry_res = get_root_level_resource(context, 'Registries', bios_registry_id)
    bios_registry_file_locations = bios_registry_res.dict['Location']
    bios_registry_file_location = None
    support_language_list = []
    language = 'en-US' if language is None else language
    for location in bios_registry_file_locations:
        support_language_list.append(location['Language'])
        if location['Language'] == language:
            bios_registry_file_location = location['Uri']
            break
    if bios_registry_file_location is None:
        raise RedfishCommonError("BIOS registry file doesn't support the language {}\nAvailable language: {}".format
                                 (language, ','.join(support_language_list)))

    # Get AttributeRegistry file content from *.json
    bios_registry_file_content = context.get(bios_registry_file_location)
    if 'RegistryEntries' not in bios_registry_file_content.dict:
        raise RedfishCommonError("BIOS registry file doesn't contain 'RegistryEntries'")
    if 'Attributes' not in bios_registry_file_content.dict['RegistryEntries']:
        raise RedfishCommonError("BIOS registry file doesn't contain 'Attributes'")
    attr_all = bios_registry_file_content.dict['RegistryEntries']['Attributes']
    if len(attr_all) == 0:
        raise RedfishCommonError("BIOS registry file doesn't contain any element in Attributes")

    # If CurrentValue is not valid, then get it from Bios.Attributes
    if 'CurrentValue' not in attr_all[0]:
        current_settings, future_settings = get_system_bios(context, system_id, False)
        for index, attr in enumerate(attr_all):
            attr_all[index]['CurrentValue'] = current_settings[attr['AttributeName']]

    return_attr = []
    if attribute is None:
        return_attr = attr_all
    else:
        for attr in attr_all:
            for attr_input in attribute:
                if attr['AttributeName'] == attr_input:
                    return_attr.append(attr)
    return return_attr


def reset_system_bios(context, system_id=None):
    """
    Finds a system matching the given ID and to load BIOS default

    Args:
        context: The Redfish client object with an open session
        system_id: The system to locate; if None, perform on the only system

    Returns:
        A rest request for POST operation
    """

    # Locate the system
    system = get_root_level_resource(context, 'Systems', system_id)

    # Get the Bios resource
    if 'Bios' not in system.dict:
        raise RedfishNoResourceError('System "{}" does not support representing BIOS'.format(system.dict['Id']))
    bios = context.get(system.dict['Bios']['@odata.id'])

    # Get Actions from bios
    if 'Actions' not in bios.dict:
        raise RedfishNoResourceError('"{}" does not support representing Actions'.format(bios.dict['Id']))
    actions = bios.dict['Actions']

    # Get @Bios.ResetBios from bios
    if '#Bios.ResetBios' not in actions:
        raise RedfishNoResourceError('Actions does not support representing #Bios.ResetBios')

    reset_bios_uri = actions['#Bios.ResetBios']['target']

    # Check if have @Redfish.ActionInfo
    if '@Redfish.ActionInfo' in actions['#Bios.ResetBios']:
        action_info = context.get(actions['#Bios.ResetBios']['@Redfish.ActionInfo'])
        if 'Parameters' in action_info.dict:
            if len(action_info.dict['Parameters']) == 1:
                if 'Name' in action_info.dict['Parameters'][0] and \
                        'AllowableValues' in action_info.dict['Parameters'][0]:
                    if 'Reset' in action_info.dict['Parameters'][0]['AllowableValues']:
                        parameter = {action_info.dict['Parameters'][0]['Name']: 'Reset'}
                        result = context.post(reset_bios_uri, body=parameter)
                        try:
                            verify_response(result)
                        except:
                            raise RedfishCommonError('POST error')
                        return result

    # If no @Redfish.ActionInfo, just POST it without body
    result = context.post(reset_bios_uri)
    try:
        verify_response(result)
    except:
        raise RedfishCommonError('POST error')
    return result


def change_bios_password(context, password_list, system_id=None):
    """
    Finds a system matching the given ID and to change BIOS password

    Args:
        context: The Redfish client object with an open session
        password_list: A list contain three strings: Password Name, Old Password, New Password
        system_id: The system to locate; if None, perform on the only system

    Returns:
        A rest request for POST operation
    """
    # Check input
    if len(password_list) != 3:
        raise RedfishCommonError('Input parameters wrong, must be three')

    # Locate the system
    system = get_root_level_resource(context, 'Systems', system_id)

    # Get the Bios resource
    if 'Bios' not in system.dict:
        raise RedfishNoResourceError('System "{}" does not support representing BIOS'.format(system.dict['Id']))
    bios = context.get(system.dict['Bios']['@odata.id'])

    # Get Actions from bios
    if 'Actions' not in bios.dict:
        raise RedfishNoResourceError('"{}" does not support representing Actions'.format(bios.dict['Id']))
    actions = bios.dict['Actions']

    # Get @Bios.ChangePassword from bios
    if '#Bios.ChangePassword' not in actions:
        raise RedfishNoResourceError('Actions does not support representing #Bios.ChangePassword')

    change_password_uri = actions['#Bios.ChangePassword']['target']
    parameters = {'PasswordName': password_list[0], 'OldPassword': password_list[1], 'NewPassword': password_list[2]}

    # POST it
    result = context.post(change_password_uri, body=parameters)
    try:
        verify_response(result)
    except:
        raise RedfishCommonError('POST error')
    return result
