#  SPDX-License-Identifier: Apache-2.0
"""
Python Package for controlling Tesla API.

For more details about this api, please refer to the documentation at
https://github.com/zabuldon/teslajsonpy
"""
import time
from typing import List, Optional, Text

from teslajsonpy.vehicle import VehicleDevice
from teslajsonpy.exceptions import UnknownPresetMode


class Climate(VehicleDevice):
    """Home-assistant class of HVAC for Tesla vehicles.

    This is intended to be partially inherited by a Home-Assitant entity.
    """

    def __init__(self, data, controller):
        """Initialize the environmental controls.

        Vehicles have both a driver and passenger.

        Parameters
        ----------
        data : dict
            The base state for a Tesla vehicle.
            https://tesla-api.timdorr.com/vehicle/state/data
        controller : teslajsonpy.Controller
            The controller that controls updates to the Tesla API.

        Returns
        -------
        None

        """
        super().__init__(data, controller)
        self.__is_auto_conditioning_on = None
        self.__inside_temp = None
        self.__outside_temp = None
        self.__driver_temp_setting = None
        self.__passenger_temp_setting = None
        self.__is_climate_on = None
        self.__fan_status = None
        self.__preset_mode: Text = None
        self.__manual_update_time = 0

        self.type = "HVAC (climate) system"
        self.hass_type = "climate"
        self.measurement = "C"

        self.name = self._name()

        self.uniq_name = self._uniq_name()
        self.bin_type = 0x3

    def is_hvac_enabled(self):
        """Return whether HVAC is running."""
        return self.__is_climate_on

    def get_current_temp(self):
        """Return vehicle inside temperature."""
        return self.__inside_temp

    def get_goal_temp(self):
        """Return driver set temperature."""
        return self.__driver_temp_setting

    def get_fan_status(self):
        """Return fan status."""
        return self.__fan_status

    async def async_update(self, wake_if_asleep=False, force=False) -> None:
        """Update the HVAC state."""
        await super().async_update(wake_if_asleep=wake_if_asleep, force=force)
        data = self._controller.get_climate_params(self._id)
        if data:
            last_update = self._controller.get_last_update_time(self._id)
            if last_update >= self.__manual_update_time:
                self.__is_auto_conditioning_on = data["is_auto_conditioning_on"]
                self.__is_climate_on = data["is_climate_on"]
                self.__driver_temp_setting = (
                    data["driver_temp_setting"]
                    if data["driver_temp_setting"]
                    else self.__driver_temp_setting
                )
                self.__passenger_temp_setting = (
                    data["passenger_temp_setting"]
                    if data["passenger_temp_setting"]
                    else self.__passenger_temp_setting
                )
            self.__inside_temp = (
                data["inside_temp"] if data["inside_temp"] else self.__inside_temp
            )
            self.__outside_temp = (
                data["outside_temp"] if data["outside_temp"] else self.__outside_temp
            )
            self.__fan_status = data["fan_status"]
            if data.get("defrost_mode") is not None:
                self.__preset_mode = (
                    "defrost" if data.get("defrost_mode") == 2 else "normal"
                )

    async def set_temperature(self, temp):
        """Set both the driver and passenger temperature to temp."""
        temp = round(temp, 1)
        self.__manual_update_time = time.time()
        data = await self._controller.command(
            self._id,
            "set_temps",
            {"driver_temp": temp, "passenger_temp": temp},
            wake_if_asleep=True,
        )
        if data and data["response"]["result"]:
            self.__driver_temp_setting = temp
            self.__passenger_temp_setting = temp

    async def set_status(self, enabled):
        """Enable or disable the HVAC."""
        self.__manual_update_time = time.time()
        if enabled:
            data = await self._controller.command(
                self._id, "auto_conditioning_start", wake_if_asleep=True
            )
            if data and data["response"]["result"]:
                self.__is_auto_conditioning_on = True
                self.__is_climate_on = True
        else:
            data = await self._controller.command(
                self._id, "auto_conditioning_stop", wake_if_asleep=True
            )
            if data and data["response"]["result"]:
                self.__is_auto_conditioning_on = False
                self.__is_climate_on = False
        await self.async_update()

    async def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self.preset_modes:
            raise UnknownPresetMode(
                f"Preset mode '{preset_mode}' is not valid. Use {self.preset_modes}"
            )
        self.__manual_update_time = time.time()
        data = await self._controller.command(
            self._id,
            "set_preconditioning_max",
            data={"on": preset_mode == "defrost"},
            wake_if_asleep=True,
        )
        if data and data["response"]["result"]:
            self.__preset_mode = preset_mode
            await self.async_update(force=True)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp.

        Requires SUPPORT_PRESET_MODE.
        """
        return self.__preset_mode

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes.

        Requires SUPPORT_PRESET_MODE.
        """
        return ["normal", "defrost"]

    @staticmethod
    def has_battery():
        """Return whether the device has a battery."""
        return False


class TempSensor(VehicleDevice):
    """Home-assistant class of temperature sensors for Tesla vehicles.

    This is intended to be partially inherited by a Home-Assitant entity.
    """

    def __init__(self, data, controller):
        """Initialize the temperature sensors and track in celsius.

        Vehicles have both a driver and passenger.

        Parameters
        ----------
        data : dict
            The base state for a Tesla vehicle.
            https://tesla-api.timdorr.com/vehicle/state/data
        controller : teslajsonpy.Controller
            The controller that controls updates to the Tesla API.

        Returns
        -------
        None

        """
        super().__init__(data, controller)
        self.__inside_temp = None
        self.__outside_temp = None

        self.type = "temperature sensor"
        self.measurement = "C"
        self.hass_type = "sensor"
        self._device_class: Text = "temperature"
        self.name = self._name()
        self.uniq_name = self._uniq_name()
        self.bin_type = 0x4

    def get_inside_temp(self):
        """Get inside temperature."""
        return self.__inside_temp

    def get_outside_temp(self):
        """Get outside temperature."""
        return self.__outside_temp

    async def async_update(self, wake_if_asleep=False, force=False) -> None:
        """Update the temperature."""
        await super().async_update(wake_if_asleep=wake_if_asleep)
        data = self._controller.get_climate_params(self._id)
        if data:
            self.__inside_temp = (
                data["inside_temp"] if data["inside_temp"] else self.__inside_temp
            )
            self.__outside_temp = (
                data["outside_temp"] if data["outside_temp"] else self.__outside_temp
            )

    @staticmethod
    def has_battery():
        """Return whether the device has a battery."""
        return False

    @property
    def device_class(self) -> Text:
        """Return the HA device class."""
        return self._device_class
