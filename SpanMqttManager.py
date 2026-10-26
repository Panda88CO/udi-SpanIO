#!/usr/bin/env python3
"""
SpanMqttManager: Asyncio MQTT Bridge for SPAN Panel v2 (Homie MQTT push streaming).

Bridges the asyncio-native span-panel-api transport with the synchronous Polyglot PG3x
udi_interface node lifecycle, featuring an eisy-friendly throttling engine:
- Minimum 30s delay between updates per panel.
- 15W power threshold to trigger updates.
- 15-minute fallback heartbeat if power changes remain under 15W.
- Immediate dispatch on discrete state changes (relay open/close, priority change).
"""

import asyncio
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    from span_panel_api import (
        create_span_client,
        register_v2,
        MqttClientConfig,
        SpanMqttClient,
        SpanPanelSnapshot,
    )
    from span_panel_api.exceptions import (
        SpanPanelError,
        SpanPanelAuthError,
        SpanPanelConnectionError,
        SpanPanelStaleDataError,
        SpanPanelTimeoutError,
        SpanPanelAPIError,
    )
    SPAN_MQTT_AVAILABLE = True
except ImportError:
    SPAN_MQTT_AVAILABLE = False
    SpanPanelSnapshot = Any
    MqttClientConfig = Any


LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DNS Override Hook for SPAN Panel mDNS Hostnames (.local)
# On platforms like eisy/FreeBSD where mDNS is not routed through getaddrinfo,
# SPAN panels report broker hostnames like span-nt-xxxx-yyyy.local.
# Python TLS verification (check_hostname=True) requires connecting to the
# broker hostname matching the server certificate, but TCP needs the IP.
# By intercepting getaddrinfo, we route .local broker hosts to the panel IP.
# ---------------------------------------------------------------------------
_ORIG_GETADDRINFO = socket.getaddrinfo
_DNS_HOST_OVERRIDES: Dict[str, str] = {}


def _custom_getaddrinfo(host, port, *args, **kwargs):
    """Intercept DNS lookups for SPAN panel .local hostnames to map to IP addresses."""
    if isinstance(host, str):
        cleaned = host.rstrip('.').lower()
        if cleaned in _DNS_HOST_OVERRIDES:
            target = _DNS_HOST_OVERRIDES[cleaned]
            return _ORIG_GETADDRINFO(target, port, *args, **kwargs)
        # Fallback for .local SPAN broker hosts
        if cleaned.endswith('.local') and len(_DNS_HOST_OVERRIDES) >= 1:
            for registered_host, target_ip in _DNS_HOST_OVERRIDES.items():
                if cleaned in registered_host or registered_host in cleaned:
                    return _ORIG_GETADDRINFO(target_ip, port, *args, **kwargs)
            unique_ips = set(_DNS_HOST_OVERRIDES.values())
            if len(unique_ips) == 1:
                return _ORIG_GETADDRINFO(next(iter(unique_ips)), port, *args, **kwargs)
    return _ORIG_GETADDRINFO(host, port, *args, **kwargs)


if socket.getaddrinfo != _custom_getaddrinfo:
    socket.getaddrinfo = _custom_getaddrinfo


class PanelStreamState:
    """Tracks connection, throttling, and state caching for a single SPAN panel."""

    def __init__(self, host: str, passphrase: Optional[str] = None, callback: Optional[Callable[[Any], None]] = None):
        self.host = host
        self.passphrase = passphrase
        self.callback = callback
        self.client: Optional[Any] = None
        self.connected = False
        self.streaming = False
        self.last_snapshot: Optional[Any] = None
        self.last_dispatch_time: float = 0.0
        self.last_panel_power: float = 0.0
        self.circuit_powers: Dict[str, float] = {}
        self.circuit_states: Dict[str, str] = {}
        self.circuit_priorities: Dict[str, str] = {}
        self.pending_timer: Optional[asyncio.TimerHandle] = None


class SpanMqttManager:
    """Thread-safe manager hosting the asyncio event loop and SPAN MQTT clients."""

    def __init__(
        self,
        min_update_interval: float = 30.0,
        power_threshold_w: float = 15.0,
        heartbeat_interval: float = 900.0,
    ):
        self.min_update_interval = min_update_interval
        self.power_threshold_w = power_threshold_w
        self.heartbeat_interval = heartbeat_interval

        self.panels: Dict[str, PanelStreamState] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        if not SPAN_MQTT_AVAILABLE:
            LOGGER.warning('span-panel-api is not installed; MQTT streaming will be disabled')

    @property
    def is_available(self) -> bool:
        return SPAN_MQTT_AVAILABLE

    def start(self) -> None:
        """Start the background asyncio event loop thread."""
        with self._lock:
            if self._running:
                return
            if not SPAN_MQTT_AVAILABLE:
                return

            self._running = True
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(target=self._run_event_loop, name='SpanMqttLoop', daemon=True)
            self.thread.start()
            LOGGER.info('SpanMqttManager background asyncio event loop thread started')

    def _run_event_loop(self) -> None:
        """Entry point for the background thread."""
        assert self.loop is not None
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            try:
                # Cancel remaining tasks
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                LOGGER.debug(f'Error cleaning up event loop tasks: {e}')
            self.loop.close()
            LOGGER.info('SpanMqttManager event loop closed')

    def add_panel(
        self,
        host: str,
        passphrase: Optional[str] = None,
        on_snapshot_callback: Optional[Callable[[Any], None]] = None,
    ) -> bool:
        """Register and start streaming for a SPAN panel."""
        if not SPAN_MQTT_AVAILABLE or not self._running or self.loop is None:
            LOGGER.warning(f'Cannot add panel {host}: MQTT manager not running')
            return False

        with self._lock:
            if host in self.panels:
                state = self.panels[host]
                state.callback = on_snapshot_callback
                if passphrase:
                    state.passphrase = passphrase
                return True

            state = PanelStreamState(host=host, passphrase=passphrase, callback=on_snapshot_callback)
            self.panels[host] = state

        # Schedule connection on the asyncio loop
        future = asyncio.run_coroutine_threadsafe(self._connect_panel_coro(state), self.loop)
        # We don't block the caller; connection proceeds asynchronously
        return True

    async def _connect_panel_coro(self, state: PanelStreamState) -> None:
        """Async task to register, resolve broker DNS, create client, and start push streaming."""
        LOGGER.info(f'Connecting to SPAN panel {state.host} via MQTT/Homie v2...')
        try:
            # Map host IP itself in override dictionary
            _DNS_HOST_OVERRIDES[state.host.rstrip('.').lower()] = state.host

            # 1. Register with the panel to obtain broker host and TLS/MQTT credentials
            LOGGER.debug(f'Registering v2 credentials with SPAN panel at {state.host}...')
            auth_resp = await register_v2(
                host=state.host,
                name="udiSpan",
                passphrase=state.passphrase,
            )

            # 2. Map panel broker hostnames to panel IP to ensure mDNS .local resolves
            # on platforms without mDNS daemon (e.g. eisy/FreeBSD) while preserving TLS SNI
            if auth_resp.ebus_broker_host:
                broker_h = auth_resp.ebus_broker_host.rstrip('.').lower()
                _DNS_HOST_OVERRIDES[broker_h] = state.host
                LOGGER.info(f'Mapped SPAN broker host {broker_h} -> {state.host}')
            if auth_resp.hostname:
                h = auth_resp.hostname.rstrip('.').lower()
                _DNS_HOST_OVERRIDES[h] = state.host
                _DNS_HOST_OVERRIDES[f'{h}.local'] = state.host
            if auth_resp.serial_number:
                s = auth_resp.serial_number.lower()
                _DNS_HOST_OVERRIDES[f'span-{s}.local'] = state.host
                _DNS_HOST_OVERRIDES[f'{s}.local'] = state.host

            mqtt_config = MqttClientConfig(
                broker_host=auth_resp.ebus_broker_host,
                username=auth_resp.ebus_broker_username,
                password=auth_resp.ebus_broker_password,
                mqtts_port=auth_resp.ebus_broker_mqtts_port,
                ws_port=auth_resp.ebus_broker_ws_port,
                wss_port=auth_resp.ebus_broker_wss_port,
            )

            # 3. Create client (connects to MQTT broker and waits for Homie device ready)
            client = await create_span_client(
                host=state.host,
                mqtt_config=mqtt_config,
                serial_number=auth_resp.serial_number,
            )
            state.client = client

            # Connection state callback
            def on_conn_change(connected: bool) -> None:
                state.connected = connected
                if connected:
                    LOGGER.info(f'SPAN panel {state.host} MQTT broker connected')
                else:
                    LOGGER.warning(f'SPAN panel {state.host} MQTT broker disconnected')

            client.register_connection_callback(on_conn_change)

            # Snapshot callback
            async def on_snapshot_async(snapshot: SpanPanelSnapshot) -> None:
                self._handle_incoming_snapshot(state, snapshot)

            client.register_snapshot_callback(on_snapshot_async)

            state.connected = True
            LOGGER.info(f'SPAN panel {state.host} connected successfully; starting push streaming')

            await client.start_streaming()
            state.streaming = True

            # Ingest initial snapshot immediately if available
            try:
                initial_snap = await client.get_snapshot()
                if initial_snap:
                    LOGGER.info(f'Retrieved initial snapshot for SPAN panel {state.host}')
                    self._handle_incoming_snapshot(state, initial_snap)
            except Exception as e:
                LOGGER.debug(f'Initial snapshot not immediately ready for {state.host}: {e}')

        except SpanPanelAuthError as e:
            LOGGER.error(f'Authentication failed for SPAN panel {state.host}: check passphrase. Error: {e}')
        except (SpanPanelConnectionError, SpanPanelTimeoutError) as e:
            LOGGER.warning(f'Could not reach SPAN panel {state.host} via MQTT: {e}; will retry in 60s')
            if self._running and self.loop is not None:
                self.loop.call_later(60.0, lambda: asyncio.run_coroutine_threadsafe(self._connect_panel_coro(state), self.loop))
        except Exception as e:
            LOGGER.exception(f'Unexpected error connecting to SPAN panel {state.host}: {e}; will retry in 60s')
            if self._running and self.loop is not None:
                self.loop.call_later(60.0, lambda: asyncio.run_coroutine_threadsafe(self._connect_panel_coro(state), self.loop))

    def _handle_incoming_snapshot(self, state: PanelStreamState, snapshot: Any) -> None:
        """Throttling & filtering engine applied to incoming MQTT snapshots."""
        now = time.time()
        state.last_snapshot = snapshot

        # 1. Check for discrete state changes (relay state, priority)
        discrete_change = False
        power_delta_exceeded = False

        current_grid_pwr = getattr(snapshot, 'instant_grid_power_w', 0.0) or 0.0
        if abs(current_grid_pwr - state.last_panel_power) >= self.power_threshold_w:
            power_delta_exceeded = True

        circuits = getattr(snapshot, 'circuits', {}) or {}
        for cid, circuit in circuits.items():
            r_state = getattr(circuit, 'relay_state', None)
            prio = getattr(circuit, 'priority', None)
            pwr = getattr(circuit, 'instant_power_w', 0.0) or 0.0

            if cid in state.circuit_states and state.circuit_states[cid] != r_state:
                discrete_change = True
            if cid in state.circuit_priorities and state.circuit_priorities[cid] != prio:
                discrete_change = True
            if cid in state.circuit_powers and abs(pwr - state.circuit_powers[cid]) >= self.power_threshold_w:
                power_delta_exceeded = True

        elapsed = now - state.last_dispatch_time
        heartbeat_due = elapsed >= self.heartbeat_interval

        # Determine if we should dispatch immediately
        if discrete_change or (elapsed >= self.min_update_interval and (power_delta_exceeded or heartbeat_due)):
            self._dispatch_snapshot(state, snapshot, now)
        else:
            # If a significant power delta occurred but we are within the 30s debounce window,
            # schedule a deferred dispatch so the latest value is sent as soon as the 30s window expires.
            if power_delta_exceeded and state.pending_timer is None and self.loop is not None:
                delay = max(0.5, self.min_update_interval - elapsed)

                def timer_callback() -> None:
                    state.pending_timer = None
                    if state.last_snapshot is not None:
                        self._dispatch_snapshot(state, state.last_snapshot, time.time())

                state.pending_timer = self.loop.call_later(delay, timer_callback)

    def _dispatch_snapshot(self, state: PanelStreamState, snapshot: Any, timestamp: float) -> None:
        """Send the snapshot to the registered Polyglot node callback and update cache."""
        if state.pending_timer is not None:
            try:
                state.pending_timer.cancel()
            except Exception:
                pass
            state.pending_timer = None

        state.last_dispatch_time = timestamp
        state.last_panel_power = getattr(snapshot, 'instant_grid_power_w', 0.0) or 0.0

        circuits = getattr(snapshot, 'circuits', {}) or {}
        for cid, circuit in circuits.items():
            state.circuit_powers[cid] = getattr(circuit, 'instant_power_w', 0.0) or 0.0
            state.circuit_states[cid] = getattr(circuit, 'relay_state', '') or ''
            state.circuit_priorities[cid] = getattr(circuit, 'priority', '') or ''

        if state.callback:
            try:
                state.callback(snapshot)
            except Exception as e:
                LOGGER.error(f'Error executing snapshot callback for {state.host}: {e}')

    def set_circuit_relay(self, host: str, circuit_id: str, relay_state: str) -> bool:
        """Thread-safe command to open/close a circuit relay via MQTT."""
        if not self._running or self.loop is None:
            return False

        state = self.panels.get(host)
        if not state or not state.client or not state.connected:
            LOGGER.warning(f'Cannot set relay for circuit {circuit_id} on {host}: panel not connected via MQTT')
            return False

        norm_state = relay_state.upper()
        if norm_state not in ('OPEN', 'CLOSED'):
            LOGGER.error(f'Invalid relay state: {relay_state}')
            return False

        async def coro() -> None:
            LOGGER.info(f'Sending MQTT set_circuit_relay({circuit_id}, {norm_state}) on {host}')
            await state.client.set_circuit_relay(circuit_id, norm_state)

        try:
            future = asyncio.run_coroutine_threadsafe(coro(), self.loop)
            future.result(timeout=10.0)
            return True
        except Exception as e:
            LOGGER.error(f'Failed to set circuit relay {circuit_id} on {host}: {e}')
            return False

    def set_circuit_priority(self, host: str, circuit_id: str, priority: str) -> bool:
        """Thread-safe command to set circuit load shedding priority via MQTT."""
        if not self._running or self.loop is None:
            return False

        state = self.panels.get(host)
        if not state or not state.client or not state.connected:
            LOGGER.warning(f'Cannot set priority for circuit {circuit_id} on {host}: panel not connected via MQTT')
            return False

        prio_map = {
            'MUST_HAVE': 'NEVER',
            'NEVER': 'NEVER',
            'NICE_TO_HAVE': 'SOC_THRESHOLD',
            'SOC_THRESHOLD': 'SOC_THRESHOLD',
            'NOT_ESSENTIAL': 'OFF_GRID',
            'NON_ESSENTIAL': 'OFF_GRID',
            'OFF_GRID': 'OFF_GRID',
        }
        norm_input = str(priority).upper().replace(' ', '_')
        wire_prio = prio_map.get(norm_input)
        if not wire_prio:
            LOGGER.error(f'Invalid circuit priority: {priority}')
            return False

        async def coro() -> None:
            LOGGER.info(f'Sending MQTT set_circuit_priority({circuit_id}, {wire_prio}) on {host}')
            await state.client.set_circuit_priority(circuit_id, wire_prio)

        try:
            future = asyncio.run_coroutine_threadsafe(coro(), self.loop)
            future.result(timeout=10.0)
            return True
        except Exception as e:
            LOGGER.error(f'Failed to set circuit priority {circuit_id} on {host}: {e}')
            return False

    def stop(self) -> None:
        """Gracefully stop streaming and close all MQTT connections."""
        with self._lock:
            if not self._running or self.loop is None:
                return
            self._running = False

        LOGGER.info('Stopping SpanMqttManager and closing MQTT panel streams...')

        async def close_all() -> None:
            for host, state in self.panels.items():
                if state.pending_timer:
                    state.pending_timer.cancel()
                if state.client:
                    try:
                        if state.streaming:
                            await state.client.stop_streaming()
                        await state.client.close()
                        LOGGER.info(f'Closed MQTT connection to SPAN panel {host}')
                    except Exception as e:
                        LOGGER.debug(f'Error closing client for {host}: {e}')

        try:
            future = asyncio.run_coroutine_threadsafe(close_all(), self.loop)
            future.result(timeout=10.0)
        except Exception as e:
            LOGGER.debug(f'Error during MQTT manager teardown: {e}')

        # Stop event loop
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        LOGGER.info('SpanMqttManager stopped')

