from redis import Redis
from pydantic import BaseModel
from helm_release_mcp.settings import get_settings


class TypedRedisClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            username=settings.redis_user,
        )

    def hget(self, instance_of: type[BaseModel], key: str, field: str) -> BaseModel | None:
        value = self.client.hget(key, field)
        if value is None:
            return None
        return instance_of.model_validate_json(value)

    def hset(self, key: str, field: str, value: BaseModel) -> None:
        self.client.hset(key, field, value.model_dump_json())

    def hgetall(self, key: str) -> list[bytes]:
        """Get all values from a hash."""
        return list(self.client.hgetall(key).values())

    def hdel(self, key: str, field: str) -> None:
        """Delete a field from a hash."""
        self.client.hdel(key, field)
