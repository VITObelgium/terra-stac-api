from enum import Enum
from typing import List, Optional, Union
from urllib.parse import urljoin

import attr
from fastapi import HTTPException, Request
from overrides import overrides
from stac_fastapi.core.core import (
    BulkTransactionsClient,
    CoreClient,
    TransactionsClient,
)
from stac_fastapi.extensions.core.transaction.request import (
    PartialCollection,
    PartialItem,
    PatchOperation,
)
from stac_fastapi.extensions.third_party.bulk_transactions import Items
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_pydantic import Collection, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes
from starlette import status
from starlette.authentication import BaseUser

from terra_stac_api.config import Settings
from terra_stac_api.db import DatabaseLogicAuth
from terra_stac_api.errors import ForbiddenError, UnauthorizedError

_auth = "_auth"
settings = Settings()


class AccessType(str, Enum):
    READ = "read"
    WRITE = "write"


def any_role_match(user_roles: List[str], resource_roles: List[str]) -> bool:
    return any(ur in resource_roles for ur in user_roles)


def is_authorized_for_collection(
    scopes: List[str], collection: dict, access_type: AccessType
) -> bool:
    return is_admin(scopes) or any_role_match(
        scopes, collection[_auth][access_type.value]
    )


async def ensure_authorized_for_collection(
    db: DatabaseLogicAuth,
    user: BaseUser,
    scopes: List[str],
    collection_id: str,
    access_type: AccessType,
) -> Collection:
    collection = await db.find_collection(collection_id=collection_id)
    if not is_authorized_for_collection(scopes, collection, access_type):
        if user.is_authenticated:
            raise ForbiddenError(
                f"Insufficient permissions for collection {collection_id}"
            )
        else:
            raise UnauthorizedError("Unauthorized, please authenticate")
    return collection


def sync_ensure_authorized_for_collection(
    db: DatabaseLogicAuth,
    user: BaseUser,
    scopes: List[str],
    collection_id: str,
    access_type: AccessType,
) -> Collection:
    collection = db.sync_find_collection(collection_id=collection_id)
    if not is_authorized_for_collection(scopes, collection, access_type):
        if user.is_authenticated:
            raise ForbiddenError(
                f"Insufficient permissions for collection {collection_id}"
            )
        else:
            raise UnauthorizedError("Unauthorized, please authenticate")
    return collection


def is_admin(scopes: List[str]) -> bool:
    return settings.role_admin in scopes


@attr.s
class CoreClientAuth(CoreClient):
    database: DatabaseLogicAuth
    landing_page_id = attr.ib(default=settings.stac_id)

    @overrides
    async def all_collections(self, **kwargs) -> stac_types.Collections:
        # TODO: implement paging
        request: Request = kwargs["request"]
        base_url = str(request.base_url)
        return stac_types.Collections(
            collections=[
                self.collection_serializer.db_to_stac(c, request=request)
                for c in await self.database.get_all_authorized_collections(
                    request.auth.scopes
                )
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
    async def get_collection(
        self, collection_id: str, **kwargs
    ) -> stac_types.Collection:
        request: Request = kwargs["request"]
        # collection = await self.database.find_collection(collection_id=collection_id)
        collection = await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.READ,
        )
        return self.collection_serializer.db_to_stac(
            collection=collection,
            request=request,
            extensions=[type(ext).__name__ for ext in self.extensions],
        )

    @overrides
    async def get_item(
        self, item_id: str, collection_id: str, **kwargs
    ) -> stac_types.Item:
        request: Request = kwargs["request"]
        await self.get_collection(
            collection_id=collection_id, request=request
        )  # getting the collection makes sure the permissions are enforced
        return await super().get_item(item_id, collection_id, **kwargs)

    @overrides
    async def post_search(
        self, search_request: BaseSearchPostRequest, request: Request
    ) -> stac_types.ItemCollection:
        collections_authorized = {
            c["id"]
            for c in await self.database.get_all_authorized_collections(
                request.auth.scopes, _source=["id"]
            )
        }
        if search_request.collections:
            # check permissions for collections in query
            if not all(c in collections_authorized for c in search_request.collections):
                if request.user.is_authenticated:
                    raise ForbiddenError("Insufficient permissions")
                else:
                    raise UnauthorizedError("Unauthorized, please authenticate")
        else:
            # only search authorized collections
            search_request.collections = (
                list(collections_authorized) if collections_authorized else None
            )
        return await super().post_search(search_request, request)


@attr.s
class TransactionsClientAuth(TransactionsClient):
    """
    TransactionsClient class which implements checking on the authorizations stored in the collection.
    Also makes sure that authorizations are configured on the collections.
    Note that no existing authorizations are checked for the :func:`create_collection` method.
    """

    database: DatabaseLogicAuth

    async def ensure_collection_auth_present(
        self, collection: Collection, request: Request
    ) -> Collection:
        """
        Make sure the collection authorizations are set. They can be provided either in the collection body (_auth)
        or the HTTP request parameters (_auth_read, _auth_write).
        Also make sure only admin users can publish public collections, or editors if they're explicitly allowed.

        :param collection: collection
        :param request: request object
        :return:
        """
        if _auth not in collection.model_extra:
            collection.model_extra[_auth] = dict()

        for at in AccessType:
            param = f"{_auth}_{at.value}"
            if param in request.query_params:
                collection.model_extra[_auth][at.value] = request.query_params.getlist(
                    param
                )
        if (
            not (
                AccessType.READ.value in collection.model_extra[_auth]
                and AccessType.WRITE.value in collection.model_extra[_auth]
            )
            or settings.role_anonymous
            in collection.model_extra[_auth][AccessType.WRITE.value]
            or (
                settings.role_anonymous
                in collection.model_extra[_auth][AccessType.READ.value]
                and not (
                    settings.role_admin in request.auth.scopes
                    or (
                        settings.role_editor in request.auth.scopes
                        and settings.editor_public_collections
                    )
                )
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid collection authorizations",
            )
        return collection

    @overrides
    async def create_item(
        self, collection_id: str, item: Union[Item, ItemCollection], **kwargs
    ) -> stac_types.Item:
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        return await super().create_item(collection_id, item, **kwargs)

    @overrides
    async def update_item(
        self, collection_id: str, item_id: str, item: Item, **kwargs
    ) -> stac_types.Item:
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        item = await super().update_item(collection_id, item_id, item, **kwargs)
        return item

    @overrides
    async def patch_item(
        self,
        collection_id: str,
        item_id: str,
        patch: Union[PartialItem, List[PatchOperation]],
        **kwargs,
    ):
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        item = await super().patch_item(collection_id, item_id, patch, **kwargs)
        return item

    @overrides
    async def delete_item(self, item_id: str, collection_id: str, **kwargs) -> None:
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        await super().delete_item(item_id, collection_id, **kwargs)

    @overrides
    async def create_collection(
        self, collection: Collection, **kwargs
    ) -> stac_types.Collection:
        collection = await self.ensure_collection_auth_present(
            collection, kwargs["request"]
        )
        return await super().create_collection(collection, **kwargs)

    @overrides
    async def update_collection(
        self, collection_id: str, collection: Collection, **kwargs
    ) -> stac_types.Collection:
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection.id,
            AccessType.WRITE,
        )
        collection = await self.ensure_collection_auth_present(
            collection, kwargs["request"]
        )
        return await super().update_collection(
            collection_id=collection_id, collection=collection, **kwargs
        )

    @overrides
    async def patch_collection(
        self,
        collection_id: str,
        patch: Union[PartialCollection, List[PatchOperation]],
        **kwargs,
    ):
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )

        return await super().patch_collection(collection_id, patch, **kwargs)

    @overrides
    async def delete_collection(self, collection_id: str, **kwargs) -> None:
        request = kwargs["request"]
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        await super().delete_collection(collection_id, **kwargs)


@attr.s
class BulkTransactionsClientAuth(BulkTransactionsClient):
    database: DatabaseLogicAuth

    async def bulk_item_insert(
        self, items: Items, chunk_size: Optional[int] = None, **kwargs
    ) -> str:
        request: Request = kwargs["request"]
        collection_id = request.path_params.get("collection_id")
        sync_ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.WRITE,
        )
        if not all(i["collection"] == collection_id for i in items.items.values()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item collection doesn't match collection path parameter {collection_id}",
            )
        return super().bulk_item_insert(items, chunk_size, refresh="wait_for", **kwargs)
