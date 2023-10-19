from datetime import datetime as datetime_type
from enum import Enum
from typing import List, Optional, Union
from urllib.parse import urljoin

from overrides import overrides
from stac_fastapi.elasticsearch.core import CoreClient, NumType
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_fastapi.types.stac import Collections, Collection, ItemCollection, Item
from fastapi import Request
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from terra_stac_api.db import DatabaseLogicAuth
from terra_stac_api.errors import ForbiddenError


class AccessType(str, Enum):
    READ = "read"
    WRITE = "write"


def any_role_match(user_roles: List[str], resource_roles: List[str]) -> bool:
    return any(ur in resource_roles for ur in user_roles)


def is_authorized_for_collection(scopes: List[str], collection: dict, access_type: AccessType) -> bool:
    return any_role_match(scopes, collection['_auth'][access_type.value])


class CoreClientAuth(CoreClient):
    database = DatabaseLogicAuth()

    @overrides
    async def all_collections(self, **kwargs) -> Collections:
        request: Request = kwargs["request"]
        base_url = str(request.base_url)
        return Collections(
            collections=[
                self.collection_serializer.db_to_stac(c, base_url=base_url)
                for c in await self.database.get_all_authorized_collections(request.auth.scopes)
            ],
            links=[
                {
                    "rel": Relations.root.value,
                    "type": MimeTypes.json,
                    "href": base_url,
                },
                {
                    "rel": Relations.parent.value,
                    "type": MimeTypes.json,
                    "href": base_url,
                },
                {
                    "rel": Relations.self.value,
                    "type": MimeTypes.json,
                    "href": urljoin(base_url, "collections"),
                },
            ],
        )

    @overrides
    async def get_collection(self, collection_id: str, **kwargs) -> Collection:
        request: Request = kwargs["request"]
        base_url = str(request.base_url)
        collection = await self.database.find_collection(collection_id=collection_id)
        if not is_authorized_for_collection(request.auth.scopes, collection, AccessType.READ):
            raise ForbiddenError(f"Insufficient permissions")
        return self.collection_serializer.db_to_stac(collection, base_url)

    @overrides
    async def get_item(self, item_id: str, collection_id: str, **kwargs) -> Item:
        request: Request = kwargs["request"]
        collection = await self.get_collection(
            collection_id=collection_id, request=request
        )  # getting the collection makes sure the permissions are enforced
        return await super().get_item(item_id, collection_id, **kwargs)

    @overrides
    async def post_search(self, search_request: BaseSearchPostRequest, **kwargs) -> ItemCollection:
        request = kwargs["request"]
        collections_authorized = {
            c["id"] for c
            in await self.database.get_all_authorized_collections(request.auth.scopes, _source=["id"])
        }
        if search_request.collections:
            # check permissions for collections in query
            if not all(c in collections_authorized for c in search_request.collections):
                raise ForbiddenError(f"Insufficient permissions")
        else:
            # only search authorized collections
            search_request.collections = list(collections_authorized)
        return await super().post_search(search_request, **kwargs)


