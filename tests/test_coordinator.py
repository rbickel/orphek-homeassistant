"""Unit tests for the Orphek data update coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.orphek.api import (
    OrphekApiError,
    OrphekConnectionError,
    OrphekDevice,
    OrphekState,
)
from custom_components.orphek.coordinator import (
    CLOUD_FETCH_INTERVAL,
    SCAN_INTERVAL,
    OrphekCoordinator,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_device():
    """Create a mock OrphekDevice."""
    device = MagicMock(spec=OrphekDevice)
    device.host = "192.168.1.100"
    device.device_id = "abc123"
    return device


@pytest.fixture
def mock_atop():
    """Create a mock OrphekAtopApi."""
    atop = MagicMock()
    atop.get_device_dps = MagicMock(return_value={})
    return atop


@pytest.fixture
def base_state():
    """A basic OrphekState for testing."""
    return OrphekState(
        is_on=True,
        channels={103: 80, 104: 60, 105: 40, 106: 20, 107: 10, 108: 5},
        mode="program",
        temperature_c=28,
    )


class TestCoordinatorInit:
    """Tests for coordinator initialization."""

    def test_scan_interval(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert coord.update_interval == SCAN_INTERVAL
        assert coord.update_interval == timedelta(seconds=30)

    def test_name_includes_host(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert "192.168.1.100" in coord.name

    def test_stores_device(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert coord.device is mock_device

    def test_atop_optional(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert coord._atop is None

    def test_atop_stored(self, mock_hass, mock_device, mock_atop):
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)
        assert coord._atop is mock_atop

    def test_poll_count_starts_at_zero(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert coord._poll_count == 0

    def test_cloud_dps_starts_empty(self, mock_hass, mock_device):
        coord = OrphekCoordinator(mock_hass, mock_device)
        assert coord._cloud_dps == {}


class TestCoordinatorUpdate:
    """Tests for the _async_update_data method."""

    @pytest.mark.asyncio
    async def test_basic_local_update(self, mock_hass, mock_device, base_state):
        """Local-only update returns state from device."""
        mock_hass.async_add_executor_job.return_value = base_state
        coord = OrphekCoordinator(mock_hass, mock_device)

        state = await coord._async_update_data()

        assert state.is_on is True
        assert state.channels[103] == 80
        mock_hass.async_add_executor_job.assert_called_once_with(
            mock_device.get_state
        )

    @pytest.mark.asyncio
    async def test_local_error_raises_update_failed(self, mock_hass, mock_device):
        """OrphekApiError from device raises UpdateFailed."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        mock_hass.async_add_executor_job.side_effect = OrphekConnectionError(
            "Connection lost"
        )
        coord = OrphekCoordinator(mock_hass, mock_device)

        with pytest.raises(UpdateFailed, match="Connection lost"):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_poll_count_increments(self, mock_hass, mock_device, base_state):
        """Poll count increments on each update."""
        mock_hass.async_add_executor_job.return_value = base_state
        coord = OrphekCoordinator(mock_hass, mock_device)

        await coord._async_update_data()
        assert coord._poll_count == 1
        await coord._async_update_data()
        assert coord._poll_count == 2

    @pytest.mark.asyncio
    async def test_no_cloud_fetch_without_atop(self, mock_hass, mock_device, base_state):
        """Without ATOP client, cloud DPS is never fetched."""
        mock_hass.async_add_executor_job.return_value = base_state
        coord = OrphekCoordinator(mock_hass, mock_device)

        for _ in range(CLOUD_FETCH_INTERVAL + 1):
            await coord._async_update_data()

        # Should only have been called with get_state, never get_device_dps
        for call in mock_hass.async_add_executor_job.call_args_list:
            assert call[0][0] == mock_device.get_state

    @pytest.mark.asyncio
    async def test_cloud_fetch_on_first_poll(self, mock_hass, mock_device, mock_atop, base_state):
        """Cloud DPS is fetched on first poll when _cloud_dps is empty."""
        cloud_dps = {"20": True, "111": "base64schedule"}

        async def side_effect(func, *args):
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                return cloud_dps
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)

        with patch.object(OrphekDevice, "update_state_from_cloud") as mock_merge:
            await coord._async_update_data()

        assert coord._cloud_dps == cloud_dps

    @pytest.mark.asyncio
    async def test_cloud_fetch_at_interval(self, mock_hass, mock_device, mock_atop, base_state):
        """Cloud DPS is fetched again after CLOUD_FETCH_INTERVAL polls."""
        cloud_call_count = 0

        async def side_effect(func, *args):
            nonlocal cloud_call_count
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                cloud_call_count += 1
                return {"20": True}
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)

        # First call fetches cloud (empty _cloud_dps)
        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()
        assert cloud_call_count == 1

        # Next CLOUD_FETCH_INTERVAL-1 calls skip cloud
        for _ in range(CLOUD_FETCH_INTERVAL - 1):
            with patch.object(OrphekDevice, "update_state_from_cloud"):
                await coord._async_update_data()
        assert cloud_call_count == 1

        # The CLOUD_FETCH_INTERVAL-th call triggers cloud again
        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()
        assert cloud_call_count == 2

    @pytest.mark.asyncio
    async def test_cloud_fetch_failure_uses_cached(self, mock_hass, mock_device, mock_atop, base_state):
        """Cloud fetch failure keeps cached data."""
        cached_dps = {"20": True, "103": 50}
        call_count = 0

        async def side_effect(func, *args):
            nonlocal call_count
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                call_count += 1
                if call_count > 1:
                    raise Exception("Cloud API error")
                return cached_dps
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)

        # First call succeeds
        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()
        assert coord._cloud_dps == cached_dps

        # Force cloud refetch by bumping poll count
        coord._poll_count = CLOUD_FETCH_INTERVAL

        # Second call fails, cached data retained
        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()
        assert coord._cloud_dps == cached_dps

    @pytest.mark.asyncio
    async def test_cloud_merge_called(self, mock_hass, mock_device, mock_atop, base_state):
        """update_state_from_cloud is called when cloud_dps is available."""
        async def side_effect(func, *args):
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                return {"103": 90}
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)

        with patch.object(OrphekDevice, "update_state_from_cloud") as mock_merge:
            state = await coord._async_update_data()
            mock_merge.assert_called_once_with(base_state, {"103": 90})

    @pytest.mark.asyncio
    async def test_no_merge_when_no_cloud_dps(self, mock_hass, mock_device, base_state):
        """update_state_from_cloud is NOT called when _cloud_dps is empty."""
        mock_hass.async_add_executor_job.return_value = base_state
        coord = OrphekCoordinator(mock_hass, mock_device)

        with patch.object(OrphekDevice, "update_state_from_cloud") as mock_merge:
            await coord._async_update_data()
            mock_merge.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_count_resets_on_cloud_fetch(self, mock_hass, mock_device, mock_atop, base_state):
        """Poll count resets to 0 after a cloud fetch."""
        async def side_effect(func, *args):
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                return {"20": True}
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)
        coord._poll_count = CLOUD_FETCH_INTERVAL - 1  # next call triggers cloud

        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()

        assert coord._poll_count == 0

    @pytest.mark.asyncio
    async def test_empty_cloud_dps_not_cached(self, mock_hass, mock_device, mock_atop, base_state):
        """Empty cloud DPS response doesn't overwrite cache."""
        async def side_effect(func, *args):
            if func == mock_device.get_state:
                return base_state
            if func == mock_atop.get_device_dps:
                return {}
            return None

        mock_hass.async_add_executor_job.side_effect = side_effect
        coord = OrphekCoordinator(mock_hass, mock_device, atop=mock_atop)
        coord._cloud_dps = {"20": True}  # existing cache

        with patch.object(OrphekDevice, "update_state_from_cloud"):
            await coord._async_update_data()

        assert coord._cloud_dps == {"20": True}  # cache preserved
