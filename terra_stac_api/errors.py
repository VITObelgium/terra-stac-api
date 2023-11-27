from stac_fastapi.api.errors import DEFAULT_STATUS_CODES
from stac_fastapi.types.errors import StacApiError
from starlette import status


class UnauthorizedError(StacApiError):
    pass


class ForbiddenError(StacApiError):
    pass


DEFAULT_STATUS_CODES[UnauthorizedError] = status.HTTP_401_UNAUTHORIZED
DEFAULT_STATUS_CODES[ForbiddenError] = status.HTTP_403_FORBIDDEN
