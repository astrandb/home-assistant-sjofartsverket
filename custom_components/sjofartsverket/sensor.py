"""
Get data from sjofartsverket.se
"""

import json
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.rest.data import RestData
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
_ENDPOINT = "https://services.viva.sjofartsverket.se:8080/output/vivaoutputservice.svc/vivastation/"

DEFAULT_NAME = "Sjöfartsverket"
DEFAULT_INTERVAL = 1
DEFAULT_VERIFY_SSL = True
CONF_LOCATION = "location"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_LOCATION, default=0): cv.string,
    }
)

SCAN_INTERVAL = timedelta(minutes=DEFAULT_INTERVAL)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    location = config.get(CONF_LOCATION)

    if "," in location:
        location = location.split(",")

    if isinstance(location, list):
        for locationId in location:
            await add_sensors(
                hass, config, async_add_devices, name, locationId, discovery_info
            )
    else:
        await add_sensors(
            hass, config, async_add_devices, name, location, discovery_info
        )


async def add_sensors(
    hass, config, async_add_devices, name, location, discovery_info=None
):
    method = "GET"
    payload = ""
    auth = None
    verify_ssl = DEFAULT_VERIFY_SSL
    headers = {}
    params = {}
    timeout = 5000
    endpoint = _ENDPOINT + location
    rest = RestData(
        hass, method, endpoint, auth, headers, payload, params, verify_ssl, timeout
    )
    await rest.async_update()

    if rest.data is None:
        _LOGGER.error("Unable to fetch data from Sjöfartsverket")
        return False
    _LOGGER.debug("rest.data: %s", rest.data)
    restData = json.loads(rest.data)
    sensors = []
    location = restData["GetSingleStationResult"]["Name"]
    for data in restData["GetSingleStationResult"]["Samples"]:
        sensors.append(entityRepresentation(rest, name, location, data))
    async_add_devices(sensors, True)


# pylint: disable=no-member
class entityRepresentation(Entity):
    """Representation of a sensor."""

    def __init__(self, rest, prefix, location, data):
        """Initialize a sensor."""
        self._rest = rest
        self._prefix = prefix
        self._location = location
        self._data = data
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._prefix}{self._name}"

    @property
    def state(self):
        """Return the state of the device."""
        if self._state is not None:
            return self._state
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the monitored installation."""
        if self._attributes is not None:
            return self._attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._unit is not None:
            return self._unit

    @property
    def device_class(self):
        if self._type == "watertemp":
            return "temperature"

    @property
    def icon(self):
        if self._type == "level":
            return "mdi:ferry"
        elif self._type == "wind":
            return "mdi:weather-windy"

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DEFAULT_NAME, self._location)},
            "name": self._location,
            "manufacturer": "Sjöfartsverket",
        }

    async def async_update(self):
        """Get the latest data from the API and updates the state."""
        try:
            getAttributes = [
                "Trend",
                "Msg",
                "Calm",
                "Heading",
                "WaterLevelReference",
                "WaterLevelOffset",
            ]

            await self._rest.async_update()
            _LOGGER.debug("%s - updated data: %s", self._data["Name"], self._rest.data)
            self._result = json.loads(self._rest.data)
            self._name = self._prefix + "_" + self._location + "_" + self._data["Name"]
            for data in self._result["GetSingleStationResult"]["Samples"]:
                if (
                    self._name
                    == self._prefix + "_" + self._location + "_" + data["Name"]
                ):
                    self._unit = data["Unit"]
                    self._state = data["Value"]
                    self._type = data["Type"]
                    self._attributes.update({"type": self._type})
                    self._attributes.update({"last_modified": data["Updated"]})
                    for attribute in data:
                        if attribute in getAttributes and data[attribute]:
                            self._attributes.update({attribute: data[attribute]})
        except TypeError as e:
            self._result = None
            _LOGGER.error("Unable to fetch data from sjofartsverket. " + str(e))
