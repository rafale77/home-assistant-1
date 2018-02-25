"""
Reads vehicle status from BMW connected drive portal.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/bmw_connected_drive/
"""
import logging
import datetime

import voluptuous as vol
from homeassistant.helpers import discovery
from homeassistant.helpers.event import track_utc_time_change

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_USERNAME, CONF_PASSWORD
)

REQUIREMENTS = ['bimmer_connected==0.4.0']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'bmw_connected_drive'
CONF_VALUES = 'values'
CONF_COUNTRY = 'country'

ACCOUNT_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_COUNTRY): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: {
        cv.string: ACCOUNT_SCHEMA
    },
}, extra=vol.ALLOW_EXTRA)


BMW_COMPONENTS = ['binary_sensor', 'device_tracker', 'lock', 'sensor', 'switch']
UPDATE_INTERVAL = 5  # in minutes


def setup(hass, config):
    """Set up the BMW connected drive components."""
    accounts = []
    for name, account_config in config[DOMAIN].items():
        username = account_config[CONF_USERNAME]
        password = account_config[CONF_PASSWORD]
        country = account_config[CONF_COUNTRY]
        _LOGGER.debug('Adding new account %s', name)
        bimmer = BMWConnectedDriveAccount(username, password, country, name)
        accounts.append(bimmer)

        # update every UPDATE_INTERVAL minutes, starting now
        # this should even out the load on the servers

        now = datetime.datetime.now()
        track_utc_time_change(
            hass, bimmer.update,
            minute=range(now.minute % UPDATE_INTERVAL, 60, UPDATE_INTERVAL),
            second=now.second)

    hass.data[DOMAIN] = accounts

    for account in accounts:
        account.update()

    for component in BMW_COMPONENTS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True


class BMWConnectedDriveAccount(object):
    """Representation of a BMW vehicle."""

    def __init__(self, username: str, password: str, country: str,
                 name: str) -> None:
        """Constructor."""
        from bimmer_connected.account import ConnectedDriveAccount

        self.account = ConnectedDriveAccount(username, password, country)
        self.name = name

    def update(self, *_):
        """Update the state of all vehicles.

        Notify all listeners about the update.
        """
        try:
            self.account.update_vehicle_states()
        except IOError as exception:
            _LOGGER.error('Error updating the vehicle state.')
            _LOGGER.exception(exception)

    def add_update_listener(self, listener):
        """Add a listener for update notifications."""
        self.account.add_update_listener(listener)
