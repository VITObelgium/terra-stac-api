from stac_fastapi.types.errors import StacApiError
from stac_fastapi.api.errors import DEFAULT_STATUS_CODES
from starlette import status


class ForbiddenError(StacApiError):
    pass


DEFAULT_STATUS_CODES[ForbiddenError] = status.HTTP_403_FORBIDDEN
