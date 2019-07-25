import argparse
import os
import sys
from collections import OrderedDict
from datetime import datetime, timedelta

from consolemenu import ConsoleMenu
from consolemenu.items import FunctionItem
from prettytable import PrettyTable
from tesuto import tesuto


class InvalidChoice(Exception):
    pass


#
# API calls
#


class API:
    def _dispatch(self, api_response):

        # Validate API response
        if api_response.status_code == 401:
            raise Exception("Invalid API token")
        if api_response.status_code == 404:
            raise Exception("Object not found")

        return api_response

    def get_emulations(self):
        """
        Fetch all emulations via Tesuto API
        """
        response = self._dispatch(tesuto.apis.Emulation.list())

        # Order emulations alphabetically by name
        response.data.sort(key=lambda x: x.name)

        # Add human-friendly ending time
        for emulation in response.data:
            ending_time = (
                datetime.fromtimestamp(emulation["end_at"])
                if emulation["end_at"]
                else None
            )
            setattr(emulation, "ending_time", ending_time)

        return response.data

    def get_emulation(self, emulation_id):
        """
        Fetch a specific emulation via the Tesuto API
        """
        response = self._dispatch(tesuto.apis.Emulation.get(emulation_id))

        return response.data

    def toggle_emulations(self, emulations, status, timer=False):
        """
        Start, suspect, or stop an emulation
        :param emulations: Set of emulation objects
        :param status: Status to set
        :param timer: Prompt user for a duration, in hours
        """
        data = {"action": status}

        # Prompt user for duration if timer is enabled
        end_time = None
        if status == "start" and timer:
            while True:
                hours = int(input("Hours to run (1-24): "))
                if hours in range(1, 25):
                    end_time = datetime.utcnow() + timedelta(hours=hours)
                    end_time = int(end_time.timestamp())  # Epoch
                    data['end_at'] = end_time
                    break
                else:
                    print("Invalid choice: {}".format(hours))

        for emulation in emulations:
            response = self._dispatch(
                tesuto.apis.Emulation.put(emulation.id, data=data)
            )

            if response.status_code == 200:
                ending_at = " (ending at {})".format(end_time) if end_time else ""
                print(
                    "Set emulation {} to {}{}".format(emulation.name, status, ending_at)
                )
            else:
                print(
                    "Failed to change status to '{}' for emulation {}".format(
                        status, emulation.name
                    )
                )
                break

        input("Press [enter] to continue...")

    def get_devices(self, emulation_id):
        """
        Fetch all devices within a specified emulation via Tesuto API
        """
        response = self._dispatch(
            tesuto.apis.EmulationDevice.list(map_args=[emulation_id])
        )

        return response.data

    def get_device(self, emulation_id, device_id):
        """
        Fetch a specific device via Tesuto API
        """
        response = self._dispatch(
            tesuto.apis.EmulationDevice.get(device_id, map_args=[emulation_id])
        )

        return response.data

    def toggle_devices(self, devices, is_enabled, prompt=True):
        """
        Enable/disable a device
        :param devices: Set of devices
        :param is_enabled: Boolean representing "enabled" state
        """
        for device in devices:
            response = self._dispatch(
                tesuto.apis.EmulationDevice.put(
                    device.id,
                    map_args=[device.emulation_id],
                    data={"is_enabled": is_enabled},
                )
            )
            if response.status_code == 200:
                print(
                    "{} device {}".format(
                        "Enabled" if is_enabled else "Disabled", device.name
                    )
                )
            else:
                print("Failed to toggle status for device {}".format(device.name))
                break
        if prompt:
            input("Press [enter] to continue...")


#
# Utilities
#


def print_table(headers, data):
    """
    Print a PrettyTable
    :param headers: Ordered dictionary of human-friendly headers to the accessors
    :param data: Table data
    """
    table = PrettyTable(["#"] + [k for k in headers.keys()])
    for i, row in enumerate(data, start=1):
        columns = [i] + [getattr(row, headers[k]) for k in headers]
        table.add_row(columns)
    print(table)


def get_user_selections(choices, prompt):
    """
    Prompt user to select one or more numeric choices.
    """
    print("Ctrl+D to exit | Enter to refresh")
    while True:
        selections = []
        try:
            raw_input = input("{}: ".format(prompt))
            if raw_input == "":
                return []
            for segment in raw_input.split(","):
                try:
                    # Range expansion
                    if "-" in segment:
                        a, b = map(int, segment.split("-"))
                        for n in range(a, b + 1):
                            selections.append(n)
                    else:
                        segment = int(segment)
                        selections.append(segment)
                except ValueError:
                    raise InvalidChoice(segment)
            # Validate selections against the provided choices
            for n in selections:
                if n not in choices:
                    raise InvalidChoice(n)
        except InvalidChoice as e:
            print("Invalid choice: {}".format(e))
        except EOFError:
            # Ctrl+D
            print("\n")
            return None
        else:
            return selections


#
# Prompts
#


def select_emulations():
    """
    Display all Tesuto emulations and prompt the user to select one or more.
    """
    while True:

        emulations = api.get_emulations()
        headers = OrderedDict(
            (
                ("Name", "name"),
                ("Region", "region"),
                ("Status", "status"),
                ("Ends (UTC)", "ending_time"),
            )
        )
        print_table(headers, emulations)

        # Prompt the user for a selection
        choices = range(1, len(emulations) + 1)
        selections = get_user_selections(choices=choices, prompt="Select emulation(s)")

        if selections is None:
            break

        if selections:
            manage_emulations([emulations[n - 1] for n in selections])


def select_devices(emulation_id):
    """
    Display all Tesuto devices and prompt the user to select one or more.
    """
    while True:

        devices = api.get_devices(emulation_id)
        headers = OrderedDict(
            (
                ("Name", "name"),
                ("Vendor", "vendor_name"),
                ("Model", "model_name"),
                ("Enabled", "is_enabled"),
            )
        )
        print_table(headers, devices)

        # Prompt the user for a selection
        choices = range(1, len(devices) + 1)
        selections = get_user_selections(choices=choices, prompt="Select device(s)")

        if selections is None:
            break

        if selections:
            manage_devices([devices[n - 1] for n in selections])


#
# Emulation/device management
#


def manage_emulations(emulations):
    """
    Start/stop/delete an emulation, or view its devices.
    :param emulations: List of emulations to manage
    """
    prologue_text = "\n".join(["{} ({})".format(e.name, e.status) for e in emulations])
    menu = ConsoleMenu(title="Manage Emulations", prologue_text=prologue_text)
    menu.append_item(
        FunctionItem(
            "Start", api.toggle_emulations, args=[emulations, "start"], should_exit=True
        )
    )
    menu.append_item(
        FunctionItem(
            "Start w/timer",
            api.toggle_emulations,
            args=[emulations, "start", True],
            should_exit=True,
        )
    )
    menu.append_item(
        FunctionItem(
            "Stop",
            api.toggle_emulations,
            args=[emulations, "suspend"],
            should_exit=True,
        )
    )
    menu.append_item(
        FunctionItem(
            "Delete", api.toggle_emulations, args=[emulations, "stop"], should_exit=True
        )
    )

    # Present this option only when managing a single emulation to enable/disable devices
    if len(emulations) == 1:
        menu.append_item(
            FunctionItem("Show Devices", select_devices, args=[emulations[0].id])
        )

    # Present this option to enable/disable multiple devices on multiple emulations
    else:
        menu.append_item(
            FunctionItem(
                "Multi-Emulation Enable/Disable Devices",
                manage_devices_across_emulations,
                args=[emulations],
            )
        )

    menu.show()


def manage_devices_across_emulations(emulations):
    """
    Enable/disable devices across a set of emulations
    :param emulations: List of emulations
    """

    # EXAMPLES:
    # assuming an emulation has the following device names:
    #     csr1,csr2,csr3,nxos-spine1,nxos-spine2,vmx1,vmx2,vmx3,eos-spine1,eos-spine2
    # Enable csr1, all vmx and all eos devices -> csr1,vmx,eos
    # Enable all csr and vmx devices -> csr,vmx
    # Enable nxos-spine1, eos-spine1, and all csr devices -> nxos-spine1,eos-spine1,csr

    user_devices = (
        input("Using a Comma Separated List\nEnter Devices (or part of hostname): ")
        .lower()
        .split(",")
    )
    to_enable = input("Enable or Disable [e/d]: ").lower()
    desired_state = False if to_enable == "d" else True

    for emulation in emulations:
        devices = api.get_devices(emulation.id)
        devices_to_toggle = []
        for device in devices:
            for sub_string in user_devices:
                if sub_string.strip() in device.name:
                    devices_to_toggle.append(device)
        print("\nUpdating Devices for Emulation: {}".format(emulation.name))
        api.toggle_devices(devices_to_toggle, desired_state, prompt=False)
    input("\nPress [Enter] to continue...\n")


def manage_devices(devices):
    """
    Enable/disable a device
    :param devices: A device object
    """
    prologue_text = "\n".join(
        [
            "{} ({})".format(d.name, "Enabled" if d.is_enabled else "Disabled")
            for d in devices
        ]
    )
    menu = ConsoleMenu(title="Emulation > Devices", prologue_text=prologue_text)
    menu.append_item(
        FunctionItem(
            "Enable", api.toggle_devices, args=[devices, True], should_exit=True
        )
    )
    menu.append_item(
        FunctionItem(
            "Disable", api.toggle_devices, args=[devices, False], should_exit=True
        )
    )

    menu.show()


#
# Main
#


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    named_args = parser.add_argument_group("Named arguments")
    named_args.add_argument(
        "-t",
        "--token",
        help="Tesuto API token from Tesuto (can also be passed as the "
        "TESUTO_API_TOKEN environment variable). Make sure to use the "
        "programmable token and not the login UI token, which expires.",
        required=False,
    )
    args = parser.parse_args()

    # Configure the Tesuto API token
    if args.token:
        tesuto.config.set("api_token", args.token)
    elif "TESUTO_API_TOKEN" in os.environ:
        tesuto.config.set("api_token", os.environ.get("TESUTO_API_TOKEN"))
    else:
        print(
            "No Tesuto API token has been provided. Specify a token with the "
            "--token parameter, or by setting the TESUTO_API_TOKEN "
            "environment variable."
        )
        sys.exit(1)

    try:
        select_emulations()
    except KeyboardInterrupt:
        print("\n")
        sys.exit()


api = API()


if __name__ == "__main__":
    main()
