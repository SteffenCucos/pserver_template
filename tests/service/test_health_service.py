
import asyncio

from unittest.mock import ANY, AsyncMock, Mock, patch

from server.service.health_service import HealthService


def test_database_health_check_returns_true_and_closes_repository() -> None:
    async def run_test() -> None:
        settings = Mock()
        repository = Mock()
        repository.enumerate = AsyncMock(return_value=[])
        repository.close = AsyncMock()
        database_settings = Mock()
        database_settings.from_env.return_value = settings
        create_repository = Mock(return_value=repository)

        with patch.dict(
            HealthService.database_health_check.__globals__,
            {"DatabaseSettings": database_settings, "create_repository": create_repository},
        ):
            assert await HealthService().database_health_check() is True

        create_repository.assert_called_once_with(
            settings=settings,
            resource_name="health",
            serializer=ANY,
        )
        serializer = create_repository.call_args.kwargs["serializer"]
        assert isinstance(serializer, HealthService.database_health_check.__globals__["MappingSerializer"])
        repository.enumerate.assert_awaited_once_with(limit=1)
        repository.close.assert_awaited_once_with()

    asyncio.run(run_test())


def test_database_health_check_returns_false_when_repository_cannot_be_created() -> None:
    async def run_test() -> None:
        create_repository = Mock(side_effect=RuntimeError("database offline"))
        with patch.dict(
            HealthService.database_health_check.__globals__, {"create_repository": create_repository}
        ):
            assert await HealthService().database_health_check() is False

    asyncio.run(run_test())


def test_database_health_check_returns_false_and_closes_repository_when_query_fails() -> None:
    async def run_test() -> None:
        repository = Mock()
        repository.enumerate = AsyncMock(side_effect=RuntimeError("query failed"))
        repository.close = AsyncMock()
        create_repository = Mock(return_value=repository)

        with patch.dict(
            HealthService.database_health_check.__globals__, {"create_repository": create_repository}
        ):
            assert await HealthService().database_health_check() is False

        repository.close.assert_awaited_once_with()

    asyncio.run(run_test())


def test_database_health_check_ignores_cleanup_failure_after_a_successful_check() -> None:
    async def run_test() -> None:
        repository = Mock()
        repository.enumerate = AsyncMock(return_value=[])
        repository.close = AsyncMock(side_effect=RuntimeError("close failed"))
        create_repository = Mock(return_value=repository)

        with patch.dict(
            HealthService.database_health_check.__globals__, {"create_repository": create_repository}
        ):
            assert await HealthService().database_health_check() is True

        repository.close.assert_awaited_once_with()

    asyncio.run(run_test())
