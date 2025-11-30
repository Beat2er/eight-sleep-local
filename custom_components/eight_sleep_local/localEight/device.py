import asyncio
import atexit
import logging
from typing import Any, Optional, List, Dict

import aiohttp
from aiohttp.client import ClientError, ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

# You can adjust the default timeout to your preference
DEFAULT_TIMEOUT = 10
CLIENT_TIMEOUT = ClientTimeout(total=DEFAULT_TIMEOUT)


class LocalEightSleep:
    """
    A refactored version of the EightSleep client that:
      - Does NOT authenticate
      - Fetches device status from a local unauthenticated endpoint
      - Expects a JSON response from /api/deviceStatus
    """

    def __init__(
            self,
            host: str = "localhost",
            port: int = 8080,
            client_session: ClientSession | None = None,
            check_data: bool = False,
    ) -> None:
        """
        Initialize the local Eight Sleep API client.

        :param host: Hostname or IP of the local device
        :param port: Port number
        :param client_session: An optional aiohttp.ClientSession
        :param check_data: If True, fetch device data immediately at init
        """
        self._host = host
        self._port = port
        self._api_session: ClientSession | None = client_session
        self._internal_session: bool = False  # Indicates if we created the session
        self._device_json_list: List[Dict[str, Any]] = []

        # Optionally fetch the data right away
        if check_data:
            # This is a synchronous call if done at __init__
            # Usually you'd do this in an async context, so in that case
            # you might prefer to do:
            #   asyncio.create_task(self._init_data())
            # or remove this parameter entirely.
            asyncio.run(self._init_data())

        # Run cleanup on exit
        atexit.register(self.at_exit)

    async def _init_data(self):
        """Helper to fetch data in an async-safe way during init if requested."""
        await self.start()
        await self.update_device_data()

    def at_exit(self) -> None:
        """
        Ensures the session is closed on exit.
        Because we're dealing with async, we need to handle both:
          - Already-running event loops
          - Potentially no event loop
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(self.stop(), loop).result()
        except RuntimeError:
            asyncio.run(self.stop())

    async def start(self) -> bool:
        """
        Initialize the client session if needed.
        """
        _LOGGER.debug("Starting local EightSleep client.")
        if not self._api_session:
            self._api_session = ClientSession(timeout=CLIENT_TIMEOUT)
            self._internal_session = True
        return True

    async def stop(self) -> None:
        """
        Close the client session if we own it.
        """
        if self._internal_session and self._api_session:
            _LOGGER.debug("Closing local EightSleep session.")
            await self._api_session.close()
            self._api_session = None
        else:
            _LOGGER.debug("No-op: Session either not created or externally managed.")

    async def update_device_data(self) -> None:
        """
        Fetch the status from the local /api/deviceStatus endpoint.
        Store the response in a rolling 10-element list (_device_json_list).
        """
        api_slug = "/api/deviceStatus"
        _LOGGER.debug(f"Fetching device data from {api_slug}")

        # Make the GET request.
        # api_request will return the parsed JSON or None if there's an error.
        data = await self.api_request("GET", api_slug, {})

        # If `data` is None, it means something went wrong (e.g., non-200 status,
        # or an exception occurred) and is already logged in `api_request`.
        if not data:
            return

        # Process the device JSON
        self.handle_device_json(data)

    def handle_device_json(self, data: Dict[str, Any]) -> None:
        """
        Keep a rolling history of up to 10 responses in `_device_json_list`.
        """
        self._device_json_list.insert(0, data)
        self._device_json_list = self._device_json_list[:10]

    @property
    def device_data(self) -> Dict[str, Any]:
        """
        Return the most recent device status JSON, if any.
        """
        if self._device_json_list:
            return self._device_json_list[0]
        return {}



    async def api_request(
            self,
            method: str,
            api_slug: str,
            data: dict[str, Any] | None = None
    ) -> Any:
        """
        Make an API request.

        Returns:
            - JSON response for 200 status
            - True for 204 status (successful POST with no content)
            - None on error
        """
        assert self._api_session is not None, "Session not initialized. Call `start()` first."
        url = f"http://{self._host}:{self._port}{api_slug}"
        try:
            kwargs = {"method": method, "url": url}
            if data is not None:
                kwargs["json"] = data
            async with self._api_session.request(**kwargs) as resp:
                if resp.status == 204:
                    return True
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.error(f"Received unexpected status code: {resp.status}")
                return None
        except (ClientError, asyncio.TimeoutError, ConnectionRefusedError) as err:
            _LOGGER.error(f"Error in API request: {err}")
            return None

    # -------------------------------------------------------------------------
    # Control Methods (POST requests)
    # -------------------------------------------------------------------------

    async def set_temperature(self, side: str, temperature_f: int, duration: int | None = None) -> bool:
        """
        Set target temperature for a side.

        :param side: "left" or "right"
        :param temperature_f: Target temperature in Fahrenheit (55-110)
        :param duration: Optional duration in seconds
        :return: True on success, False on failure
        """
        if temperature_f < 55 or temperature_f > 110:
            _LOGGER.error(f"Temperature {temperature_f} out of range (55-110)")
            return False

        payload: Dict[str, Any] = {
            side: {
                "targetTemperatureF": temperature_f
            }
        }
        if duration is not None:
            payload[side]["secondsRemaining"] = duration

        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def turn_on(self, side: str, duration: int = 43200) -> bool:
        """
        Turn on a bed side.

        :param side: "left" or "right"
        :param duration: Duration in seconds (default 12 hours)
        :return: True on success, False on failure
        """
        payload = {
            side: {
                "isOn": True,
                "secondsRemaining": duration
            }
        }
        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def turn_off(self, side: str) -> bool:
        """
        Turn off a bed side.

        :param side: "left" or "right"
        :return: True on success, False on failure
        """
        payload = {
            side: {
                "isOn": False
            }
        }
        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def stop_alarm(self, side: str) -> bool:
        """
        Stop/clear an active alarm.

        :param side: "left" or "right"
        :return: True on success, False on failure
        """
        payload = {
            side: {
                "isAlarmVibrating": False
            }
        }
        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def start_priming(self) -> bool:
        """
        Start the pod priming process.

        :return: True on success, False on failure
        """
        payload = {
            "isPriming": True
        }
        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def set_led_brightness(self, brightness: int) -> bool:
        """
        Set LED brightness on the hub.

        :param brightness: Brightness level (0-100)
        :return: True on success, False on failure
        """
        if brightness < 0 or brightness > 100:
            _LOGGER.error(f"LED brightness {brightness} out of range (0-100)")
            return False

        payload = {
            "settings": {
                "ledBrightness": brightness
            }
        }
        result = await self.api_request("POST", "/api/deviceStatus", payload)
        return result is not None and result is not False

    async def trigger_alarm(
            self,
            side: str,
            intensity: int = 80,
            pattern: str = "rise",
            duration: int = 60
    ) -> bool:
        """
        Trigger alarm vibration immediately.

        :param side: "left" or "right"
        :param intensity: Vibration intensity 1-100 (default 80)
        :param pattern: "rise" or "double" (default "rise")
        :param duration: Duration in seconds 0-180 (default 60)
        :return: True on success, False on failure
        """
        if intensity < 1 or intensity > 100:
            _LOGGER.error(f"Alarm intensity {intensity} out of range (1-100)")
            return False
        if pattern not in ("rise", "double"):
            _LOGGER.error(f"Invalid alarm pattern: {pattern}")
            return False
        if duration < 0 or duration > 180:
            _LOGGER.error(f"Alarm duration {duration} out of range (0-180)")
            return False

        payload = {
            "side": side,
            "vibrationIntensity": intensity,
            "vibrationPattern": pattern,
            "duration": duration
        }
        result = await self.api_request("POST", "/api/alarm", payload)
        return result is not None and result is not False

    async def get_schedules(self) -> Dict[str, Any] | None:
        """
        Get all schedules including alarm settings.

        :return: Schedules dict or None on error
        """
        return await self.api_request("GET", "/api/schedules", None)

    async def update_alarm_schedule(self, side: str, schedule_data: Dict[str, Any]) -> bool:
        """
        Update alarm schedule for a side.

        :param side: "left" or "right"
        :param schedule_data: Dict with day keys and alarm settings
            Example: {"monday": {"time": "07:00", "enabled": True, ...}, ...}
        :return: True on success, False on failure
        """
        # Build payload with alarm data for each day
        payload: Dict[str, Any] = {side: {}}
        for day, alarm_settings in schedule_data.items():
            payload[side][day] = {"alarm": alarm_settings}

        result = await self.api_request("POST", "/api/schedules", payload)
        return result is not None and result is not False

    async def get_presence(self) -> Dict[str, Any] | None:
        """
        Get presence status for both sides.

        :return: Dict with left/right presence or None on error
            Example: {
                "left": {"present": true, "lastUpdated": "2025-01-15T08:30:00Z"},
                "right": {"present": false, "lastUpdated": "2025-01-15T07:45:00Z"}
            }
        """
        return await self.api_request("GET", "/api/presence", None)

    # -------------------------------------------------------------------------
    # Health Metrics Methods
    # -------------------------------------------------------------------------

    async def get_vitals(
        self,
        side: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None
    ) -> List[Dict[str, Any]] | None:
        """
        Get raw vitals records (heart rate, HRV, breathing rate).

        :param side: "left" or "right" (optional)
        :param start_time: ISO datetime string (optional)
        :param end_time: ISO datetime string (optional)
        :return: List of vitals records or None on error
        """
        params = []
        if side:
            params.append(f"side={side}")
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")

        query = f"?{'&'.join(params)}" if params else ""
        return await self.api_request("GET", f"/api/metrics/vitals{query}", None)

    async def get_vitals_summary(
        self,
        side: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None
    ) -> Dict[str, Any] | None:
        """
        Get aggregated vitals summary (avg/min/max heart rate, avg HRV, avg breathing rate).

        :param side: "left" or "right" (optional)
        :param start_time: ISO datetime string (optional)
        :param end_time: ISO datetime string (optional)
        :return: Summary dict or None on error
        """
        params = []
        if side:
            params.append(f"side={side}")
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")

        query = f"?{'&'.join(params)}" if params else ""
        return await self.api_request("GET", f"/api/metrics/vitals/summary{query}", None)

    async def get_sleep_records(
        self,
        side: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None
    ) -> List[Dict[str, Any]] | None:
        """
        Get sleep session records.

        :param side: "left" or "right" (optional)
        :param start_time: Filter by left_bed_at >= startTime (optional)
        :param end_time: Filter by entered_bed_at <= endTime (optional)
        :return: List of sleep records or None on error
        """
        params = []
        if side:
            params.append(f"side={side}")
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")

        query = f"?{'&'.join(params)}" if params else ""
        return await self.api_request("GET", f"/api/metrics/sleep{query}", None)

    async def get_movement(
        self,
        side: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None
    ) -> List[Dict[str, Any]] | None:
        """
        Get movement records.

        :param side: "left" or "right" (optional)
        :param start_time: ISO datetime string (optional)
        :param end_time: ISO datetime string (optional)
        :return: List of movement records or None on error
        """
        params = []
        if side:
            params.append(f"side={side}")
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")

        query = f"?{'&'.join(params)}" if params else ""
        return await self.api_request("GET", f"/api/metrics/movement{query}", None)

    # -------------------------------------------------------------------------
    # Below are convenience properties to pull out the fields from the JSON.
    # Adjust/extend these as you see fit. This matches the sample JSON structure
    # you provided:
    #
    # {
    #   "left": {
    #     "currentTemperatureF": 83,
    #     "targetTemperatureF": 90,
    #     "secondsRemaining": 300,
    #     "isAlarmVibrating": true,
    #     "isOn": true
    #   },
    #   "right": {...},
    #   "waterLevel": "true",
    #   "isPriming": false,
    #   "settings": {...},
    #   "sensorLabel": "\"00000-0000-000-00000\""
    # }
    # -------------------------------------------------------------------------

    @property
    def is_priming(self) -> bool:
        """
        Indicates if the device is currently priming.
        """
        return self.device_data.get("isPriming", False)

    @property
    def water_level(self) -> str:
        """
        Indicates water level status. It's a string in your sample ("true"/"false").
        You could convert to bool if you prefer.
        """
        return self.device_data.get("waterLevel", "false")

    @property
    def left_current_temp_f(self) -> Optional[int]:
        """
        The 'currentTemperatureF' on the left side (if present).
        """
        left_side = self.device_data.get("left", {})
        return left_side.get("currentTemperatureF")

    @property
    def left_target_temp_f(self) -> Optional[int]:
        left_side = self.device_data.get("left", {})
        return left_side.get("targetTemperatureF")

    @property
    def left_seconds_remaining(self) -> Optional[int]:
        left_side = self.device_data.get("left", {})
        return left_side.get("secondsRemaining")

    @property
    def left_is_alarm_vibrating(self) -> bool:
        left_side = self.device_data.get("left", {})
        return left_side.get("isAlarmVibrating", False)

    @property
    def left_is_on(self) -> bool:
        left_side = self.device_data.get("left", {})
        return left_side.get("isOn", False)

    @property
    def right_current_temp_f(self) -> Optional[int]:
        right_side = self.device_data.get("right", {})
        return right_side.get("currentTemperatureF")

    @property
    def right_target_temp_f(self) -> Optional[int]:
        right_side = self.device_data.get("right", {})
        return right_side.get("targetTemperatureF")

    @property
    def right_seconds_remaining(self) -> Optional[int]:
        right_side = self.device_data.get("right", {})
        return right_side.get("secondsRemaining")

    @property
    def right_is_alarm_vibrating(self) -> bool:
        right_side = self.device_data.get("right", {})
        return right_side.get("isAlarmVibrating", False)

    @property
    def right_is_on(self) -> bool:
        right_side = self.device_data.get("right", {})
        return right_side.get("isOn", False)

    @property
    def sensor_label(self) -> str:
        """
        A label or ID for the sensor, if present in the JSON.
        """
        return self.device_data.get("sensorLabel", "")

    @property
    def settings(self) -> Dict[str, Any]:
        """
        The `settings` object from the JSON.
        """
        return self.device_data.get("settings", {})


# Example usage (if you had a local running device):
# async def main():
#     client = LocalEightSleep(host="192.168.1.100", port=3000)
#     await client.start()
#     await client.update_device_data()
#     print("Left side current temp (F):", client.left_current_temp_f)
#     print("Is priming:", client.is_priming)
#     await client.stop()
#
# asyncio.run(main())
