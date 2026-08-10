import io
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "home/.local/bin/zenwolf-bluetooth"
)
APP = runpy.run_path(str(SCRIPT))

ADAPTER_INTERFACE = APP["ADAPTER_INTERFACE"]
DEVICE_INTERFACE = APP["DEVICE_INTERFACE"]
BluetoothError = APP["BluetoothError"]
Device = APP["Device"]
Scanner = APP["Scanner"]
device_for_choice = APP["device_for_choice"]
device_is_anonymous = APP["device_is_anonymous"]
device_label = APP["device_label"]
device_state = APP["device_state"]
find_device = APP["find_device"]
launch_waybar_manager = APP["launch_waybar_manager"]
read_adapter = APP["read_adapter"]
read_devices = APP["read_devices"]
remove_device = APP["remove_device"]
removal_phrase = APP["removal_phrase"]
run_bluetooth_command = APP["run_bluetooth_command"]
setup_device = APP["setup_device"]
visible_devices = APP["visible_devices"]

ADAPTER_PATH = "/org/bluez/hci0"
CONTROLLER_PATH = f"{ADAPTER_PATH}/dev_AA_BB_CC_DD_EE_01"
HEADSET_PATH = f"{ADAPTER_PATH}/dev_AA_BB_CC_DD_EE_02"


def dbus_value(signature: str, data: object) -> dict:
    return {
        "type": signature,
        "data": data,
    }


def adapter_properties() -> dict:
    return {
        "Alias": dbus_value("s", "zenwolf"),
        "Address": dbus_value("s", "11:22:33:44:55:66"),
        "Powered": dbus_value("b", True),
        "Discovering": dbus_value("b", False),
        "Discoverable": dbus_value("b", False),
        "Pairable": dbus_value("b", False),
    }


def device_properties(
    *,
    alias: str,
    address: str,
    connected: bool,
    paired: bool,
    trusted: bool,
    name: str | None = None,
    address_type: str | None = None,
    rssi: int | None = None,
    manufacturer_data: dict | None = None,
) -> dict:
    properties = {
        "Adapter": dbus_value("o", ADAPTER_PATH),
        "Alias": dbus_value("s", alias),
        "Address": dbus_value("s", address),
        "Paired": dbus_value("b", paired),
        "Bonded": dbus_value("b", paired),
        "Trusted": dbus_value("b", trusted),
        "Connected": dbus_value("b", connected),
        "Blocked": dbus_value("b", False),
    }
    if name is not None:
        properties["Name"] = dbus_value("s", name)
    if address_type is not None:
        properties["AddressType"] = dbus_value("s", address_type)
    if rssi is not None:
        properties["RSSI"] = dbus_value("n", rssi)
    if manufacturer_data is not None:
        properties["ManufacturerData"] = dbus_value(
            "a{qv}", manufacturer_data
        )
    return properties


def managed_objects() -> dict:
    return {
        ADAPTER_PATH: {
            ADAPTER_INTERFACE: adapter_properties(),
        },
        CONTROLLER_PATH: {
            DEVICE_INTERFACE: device_properties(
                alias="Controller",
                address="AA:BB:CC:DD:EE:01",
                connected=False,
                paired=True,
                trusted=True,
            ),
        },
        HEADSET_PATH: {
            DEVICE_INTERFACE: device_properties(
                alias="Headset",
                address="AA:BB:CC:DD:EE:02",
                connected=True,
                paired=True,
                trusted=True,
            ),
        },
    }


class StateTests(unittest.TestCase):
    def test_reads_adapter(self) -> None:
        adapter = read_adapter(managed_objects())

        self.assertEqual(adapter.alias, "zenwolf")
        self.assertTrue(adapter.powered)
        self.assertFalse(adapter.discovering)

    def test_connected_devices_sort_first(self) -> None:
        devices = read_devices(managed_objects(), ADAPTER_PATH)

        self.assertEqual(
            [device.alias for device in devices],
            ["Headset", "Controller"],
        )

    def test_missing_adapter_is_an_error(self) -> None:
        with self.assertRaises(BluetoothError):
            read_adapter({})


class MenuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.devices = read_devices(managed_objects(), ADAPTER_PATH)

    def test_selects_numbered_device(self) -> None:
        self.assertEqual(
            device_for_choice("2", self.devices).alias,
            "Controller",
        )

    def test_rejects_invalid_device_choice(self) -> None:
        for choice in ("", "0", "3", "controller"):
            with self.subTest(choice=choice):
                self.assertIsNone(
                    device_for_choice(choice, self.devices)
                )

    def test_formats_device_state(self) -> None:
        device = Device(
            path=CONTROLLER_PATH,
            adapter_path=ADAPTER_PATH,
            alias="Controller",
            address="AA:BB:CC:DD:EE:01",
            paired=True,
            bonded=True,
            trusted=True,
            connected=False,
            blocked=False,
        )

        self.assertEqual(
            device_state(device),
            "disconnected, paired, trusted, bonded",
        )

    def test_finds_device_case_insensitively(self) -> None:
        device = find_device(
            self.devices,
            "aa:bb:cc:dd:ee:01",
        )

        self.assertEqual(device.alias, "Controller")

    def test_removal_phrase_includes_full_address(self) -> None:
        device = find_device(
            self.devices,
            "AA:BB:CC:DD:EE:01",
        )

        self.assertEqual(
            removal_phrase(device),
            "REMOVE AA:BB:CC:DD:EE:01",
        )

    def test_labels_and_hides_anonymous_apple_signal(self) -> None:
        objects = managed_objects()
        objects[f"{ADAPTER_PATH}/dev_12_34_56_78_9A_BC"] = {
            DEVICE_INTERFACE: device_properties(
                alias="12-34-56-78-9A-BC",
                address="12:34:56:78:9A:BC",
                connected=False,
                paired=False,
                trusted=False,
                address_type="random",
                rssi=-52,
                manufacturer_data={
                    "76": dbus_value("ay", [1, 2, 3]),
                },
            ),
        }
        devices = read_devices(objects, ADAPTER_PATH)
        anonymous = find_device(devices, "12:34:56:78:9A:BC")

        self.assertTrue(device_is_anonymous(anonymous))
        self.assertEqual(device_label(anonymous), "Apple device (unnamed)")
        self.assertEqual(anonymous.address_type, "random")
        self.assertEqual(anonymous.rssi, -52)
        self.assertEqual(anonymous.manufacturer_ids, (76,))
        self.assertNotIn(anonymous, visible_devices(devices, False))
        self.assertIn(anonymous, visible_devices(devices, True))


class CommandTests(unittest.TestCase):
    def test_runs_command_without_a_shell(self) -> None:
        completed = Mock()
        completed.returncode = 0

        with patch.object(
            APP["subprocess"],
            "run",
            return_value=completed,
        ) as run:
            run_bluetooth_command(
                "/usr/bin/bluetoothctl",
                ["connect", "AA:BB:CC:DD:EE:01"],
            )

        run.assert_called_once_with(
            [
                "/usr/bin/bluetoothctl",
                "connect",
                "AA:BB:CC:DD:EE:01",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=(
                APP["ACTION_TIMEOUT_SECONDS"]
                + APP["PROCESS_STOP_TIMEOUT_SECONDS"]
            ),
        )

    def test_reports_bluetoothctl_failure(self) -> None:
        completed = Mock()
        completed.returncode = 1
        completed.stderr = "Connection attempt failed"
        completed.stdout = ""

        with patch.object(
            APP["subprocess"],
            "run",
            return_value=completed,
        ):
            with self.assertRaisesRegex(
                BluetoothError,
                "Connection attempt failed",
            ):
                run_bluetooth_command(
                    "/usr/bin/bluetoothctl",
                    ["connect", "AA:BB:CC:DD:EE:01"],
                )

    def test_refuses_to_remove_connected_device(self) -> None:
        connected = Device(
            path=CONTROLLER_PATH,
            adapter_path=ADAPTER_PATH,
            alias="Controller",
            address="AA:BB:CC:DD:EE:01",
            paired=True,
            bonded=True,
            trusted=True,
            connected=True,
            blocked=False,
        )
        command = Mock()

        with patch.dict(
            remove_device.__globals__,
            {"run_bluetooth_command": command},
        ):
            with self.assertRaisesRegex(
                BluetoothError,
                "Disconnect the device",
            ):
                remove_device(
                    "/usr/bin/busctl",
                    "/usr/bin/bluetoothctl",
                    connected,
                )

        command.assert_not_called()

    def test_setup_orders_pair_trust_and_connect(self) -> None:
        unpaired = Device(
            path=CONTROLLER_PATH,
            adapter_path=ADAPTER_PATH,
            alias="Controller",
            address="AA:BB:CC:DD:EE:01",
            paired=False,
            bonded=False,
            trusted=False,
            connected=False,
            blocked=False,
        )
        paired = Device(
            **{
                **unpaired.__dict__,
                "paired": True,
                "bonded": True,
            }
        )
        trusted = Device(
            **{
                **paired.__dict__,
                "trusted": True,
            }
        )
        connected = Device(
            **{
                **trusted.__dict__,
                "connected": True,
            }
        )
        command = Mock()
        wait = Mock(
            side_effect=[paired, trusted, connected]
        )

        with patch.dict(
            setup_device.__globals__,
            {
                "run_bluetooth_command": command,
                "wait_for_device_property": wait,
            },
        ):
            with redirect_stdout(io.StringIO()):
                setup_device(
                    "/usr/bin/busctl",
                    "/usr/bin/bluetoothctl",
                    unpaired,
                )

        self.assertEqual(
            [call.args[1] for call in command.call_args_list],
            [
                ["pair", "AA:BB:CC:DD:EE:01"],
                ["trust", "AA:BB:CC:DD:EE:01"],
                ["connect", "AA:BB:CC:DD:EE:01"],
            ],
        )
        self.assertEqual(
            [call.args[2] for call in wait.call_args_list],
            ["paired", "trusted", "connected"],
        )


class ScannerTests(unittest.TestCase):
    def test_starts_and_stops_owned_discovery(self) -> None:
        process = Mock()
        process.poll.return_value = None
        process.stdin = Mock()

        with patch.object(
            APP["subprocess"],
            "Popen",
            return_value=process,
        ) as popen:
            scanner = Scanner("/usr/bin/bluetoothctl")
            scanner.start(read_adapter(managed_objects()))

            popen.assert_called_once_with(
                ["/usr/bin/bluetoothctl"],
                stdin=APP["subprocess"].PIPE,
                stdout=APP["subprocess"].DEVNULL,
                stderr=APP["subprocess"].DEVNULL,
                text=True,
            )
            process.stdin.write.assert_called_with(
                "pairable on\ndiscoverable on\nscan on\n"
            )
            self.assertTrue(scanner.active)

            scanner.stop()

        process.stdin.write.assert_called_with(
            "scan off\ndiscoverable off\npairable off\nquit\n"
        )
        process.wait.assert_called_once_with(
            timeout=APP["PROCESS_STOP_TIMEOUT_SECONDS"]
        )
        self.assertFalse(scanner.active)


class LauncherTests(unittest.TestCase):
    def test_duplicate_click_exits_before_opening_ghostty(self) -> None:
        run = Mock()

        with patch.dict(
            launch_waybar_manager.__globals__,
            {
                "acquire_instance_lock": Mock(
                    side_effect=BluetoothError("already open")
                ),
            },
        ):
            with patch.object(APP["subprocess"], "run", run):
                self.assertEqual(launch_waybar_manager(), 0)

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
