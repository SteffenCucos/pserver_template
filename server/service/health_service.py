
import logging

from persistence import DatabaseSettings, MappingSerializer
from persistence.repository.factory import create_repository


logger = logging.getLogger(__name__)


class HealthService:
    """
    Health check for required services.
    """

    async def database_health_check(self) -> bool:
        """
        Safely verifies that the DB is healthy.
        """
        repository = None
        try:
            repository = create_repository(
                settings=DatabaseSettings.from_env(),
                resource_name="health",
                serializer=MappingSerializer(),
            )
            await repository.enumerate(limit=1)
            return True
        except Exception as err:
            logger.error(err)
            return False
        finally:
            if repository is not None:
                try:
                    await repository.close()
                except Exception as err:
                    logger.error(err)
