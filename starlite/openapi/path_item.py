from typing import TYPE_CHECKING, Callable, Dict, Optional, cast

from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import Operation, PathItem, RequestBody
from pydantic.fields import ModelField
from starlette.routing import get_name

from starlite.handlers import RouteHandler
from starlite.openapi.config import SchemaGenerationConfig
from starlite.openapi.parameters import create_parameters, create_path_parameter
from starlite.openapi.responses import create_responses
from starlite.openapi.schema import create_schema
from starlite.openapi.utils import get_media_type
from starlite.utils.model import create_function_signature_model

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Route


def create_request_body(route_handler: RouteHandler, handler_fields: Dict[str, ModelField]) -> Optional[RequestBody]:
    """
    Create a RequestBody model for the given RouteHandler or return None
    """
    if "data" in handler_fields:
        return RequestBody(
            content={
                get_media_type(route_handler): OpenAPISchemaMediaType(
                    media_type_schema=create_schema(handler_fields["data"])
                )
            }
        )
    return None


def create_path_item(route: "Route", config: SchemaGenerationConfig) -> PathItem:
    """
    Create a PathItem model for the given route parsing all http_methods into Operation Models
    """
    path_item = PathItem(parameters=list(map(create_path_parameter, route.path_parameters)) or None)
    for http_method, route_handler in route.route_handler_map.items():
        if route_handler.include_in_schema:
            handler_fields = create_function_signature_model(fn=cast(Callable, route_handler.fn)).__fields__
            parameters = (
                create_parameters(
                    route_handler=route_handler,
                    handler_fields=handler_fields,
                    path_parameters=route.path_parameters,
                )
                or None
            )
            raises_validation_error = bool("data" in handler_fields or path_item.parameters or parameters)
            handler_name = get_name(route_handler.fn)
            operation = Operation(
                operationId=route_handler.operation_id or handler_name,
                tags=route_handler.tags,
                summary=route_handler.summary,
                description=route_handler.description,
                deprecated=route_handler.deprecated,
                responses=create_responses(
                    route_handler=route_handler,
                    raises_validation_error=raises_validation_error,
                    default_response_headers=config.response_headers,
                ),
                requestBody=create_request_body(route_handler=route_handler, handler_fields=handler_fields),
                parameters=parameters,
            )
            setattr(path_item, http_method, operation)
    return path_item
