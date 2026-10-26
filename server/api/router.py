
import logging

from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import Any, cast

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, JSONResponse
from persistence.serializing_middleware import get_application_serializer

from api.authentication.endpoint_types import EndpointT
from api.authentication.route import AuthzRoute


serializer = get_application_serializer()



logger = logging.getLogger(__name__)


class Router(APIRouter):
    '''
    Custom router that runs simpler serialization logic to avoid certain
    pitfalls of FastAPIs standard serialization scheme. The specific use
    cases for us is that FastAPI doesn't support the case where a dataclass
    extends a non dataclass, and it doesn't support serializing enums.

    AuthzRoute is installed by default so route-level auth annotations are
    converted into FastAPI dependencies during route registration.
    '''

    def __init__(self, *positional: Any, **named: Any) -> None:
        named.setdefault("route_class", AuthzRoute)
        logger.info(f"Initialized router: {named.get('prefix', '')}")
        super().__init__(*positional, **named)

    # 
    def get(self, *args: Any, **kwargs: Any) -> Callable[[EndpointT], EndpointT]:
        def get_decorator(func: EndpointT) -> EndpointT:
            return super(Router, self).get(*args, **kwargs)(Router.get_serialize_wrapper(func))

        return get_decorator

    def post(self, *args: Any, **kwargs: Any) -> Callable[[EndpointT], EndpointT]:
        def post_decorator(func: EndpointT) -> EndpointT:
            return super(Router, self).post(*args, **kwargs)(Router.get_serialize_wrapper(func))

        return post_decorator

    def put(self, *args: Any, **kwargs: Any) -> Callable[[EndpointT], EndpointT]:
        def put_decorator(func: EndpointT) -> EndpointT:
            return super(Router, self).put(*args, **kwargs)(Router.get_serialize_wrapper(func))

        return put_decorator

    def delete(self, *args: Any, **kwargs: Any) -> Callable[[EndpointT], EndpointT]:
        def delete_decorator(func: EndpointT) -> EndpointT:
            return super(Router, self).delete(*args, **kwargs)(Router.get_serialize_wrapper(func))

        return delete_decorator

    def patch(self, *args: Any, **kwargs: Any) -> Callable[[EndpointT], EndpointT]:
        def patch_decorator(func: EndpointT) -> EndpointT:
            return super(Router, self).patch(*args, **kwargs)(Router.get_serialize_wrapper(func))

        return patch_decorator

    @staticmethod
    def get_serialize_wrapper(func: EndpointT) -> EndpointT:
        # Preserve the endpoint execution model. FastAPI runs synchronous route
        # handlers in its thread pool, while async handlers must be awaited on
        # the event loop before their result can be serialized.
        json_serialize: Any = None
        if iscoroutinefunction(func):
            @wraps(
                func,
                assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            )
            async def async_json_serialize(*positional: Any, **named: Any) -> Response:
                result = await func(*positional, **named)
                return Router._serialize_result(result)
            json_serialize = async_json_serialize
        else:
            @wraps(
                func,
                assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            )
            def sync_json_serialize(*positional: Any, **named: Any) -> Response:
                result = func(*positional, **named)
                return Router._serialize_result(result)
            json_serialize = sync_json_serialize
        
        json_serialize.__signature__ = signature(func)
        return cast(EndpointT, json_serialize)

    @staticmethod
    def _serialize_result(result: Response) -> Response:
        if isinstance(result, HTMLResponse):
            return result
        return JSONResponse(content=serializer.serialize(result))
