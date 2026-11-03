import logging

import attr
from opensearchpy.helpers import async_scan
from stac_fastapi.opensearch.config import AsyncOpensearchSettings
from stac_fastapi.opensearch.database_logic import create_index_templates
from stac_fastapi.sfeos_helpers.mappings import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    ITEMS_ALIAS_PREFIX,
    ITEMS_INDEX_PREFIX,
)

import terra_stac_api.db  # noqa: F401 (applies the custom collection mappings)

logger = logging.getLogger(__name__)


@attr.s
class Migration:
    async def run(self):
        pass

    @classmethod
    async def run_all(cls):
        for migration in cls.__subclasses__():
            logger.info("Running migration: %s", migration.__name__)
            await migration().run()


"""
Migrations to complete:
 - Remove old "/_template/template_${COLLECTIONS_INDEX}" and "/_template/template_${ITEMS_INDEX_PREFIX}" templates (deprecated and replaced by the new "/_index_template/template_..." templates)
 - Check the collections index for the correct mappings and settings, reindex if necessary
 - Create a case-sensitive alias for item indices, so that queries with a case-sensitive "collection" field can be routed to the correct index

Currently, the mappings of item indices are not checked or re-indexed as this may be a very expensive operation. 
The item indices have dynamic mappings, so they are less likely to need a migration.
"""
COLLECTIONS_TEMPLATE = f"template_{COLLECTIONS_INDEX}"
ITEMS_TEMPLATE = f"template_{ITEMS_INDEX_PREFIX}"


class AliasMigration(Migration):
    """
    Add a case-sensitive alias for item indices
    """

    async def run(self):
        async with AsyncOpensearchSettings().create_client as client:
            if await client.indices.exists(index=COLLECTIONS_INDEX):
                async for c in async_scan(
                    client, index=COLLECTIONS_INDEX, query={"query": {"match_all": {}}}
                ):
                    collection_id = c["_source"]["id"]
                    index_wildcard = f"{ITEMS_INDEX_PREFIX}{collection_id.lower()}*"
                    alias_name = f"{ITEMS_ALIAS_PREFIX}{collection_id}"
                    if not await client.indices.exists_alias(
                        name=alias_name, index=index_wildcard
                    ):
                        # get index name for the collection
                        index_name = list(
                            (await client.indices.get(index=index_wildcard)).keys()
                        )[0]
                        await client.indices.put_alias(
                            index=index_name, name=alias_name
                        )
                        logger.info(
                            "Created alias %s for index %s", alias_name, index_name
                        )


class LegacyTemplateMigration(Migration):
    """
    Remove the old "/_template/template_${COLLECTIONS_INDEX}" and "/_template/template_${ITEMS_INDEX_PREFIX}" templates, if they exist.
    """

    async def run(self):
        async with AsyncOpensearchSettings().create_client as client:
            # Remove the old templates if they exist
            if await client.indices.exists_template(name=COLLECTIONS_TEMPLATE):
                await client.indices.delete_template(name=COLLECTIONS_TEMPLATE)
            if await client.indices.exists_template(name=ITEMS_TEMPLATE):
                await client.indices.delete_template(name=ITEMS_TEMPLATE)


class CollectionMappingMigration(Migration):
    """
    Check the collections index for the correct mappings and settings, reindex if necessary
    """

    async def run(self):
        async with AsyncOpensearchSettings().create_client as client:
            # Check the collections index for the correct mappings and settings, reindex if necessary
            if not await client.indices.exists_index_template(
                name=COLLECTIONS_TEMPLATE
            ):
                return
            index_templates = await client.indices.get_index_template(
                name=COLLECTIONS_TEMPLATE
            )
            current_mapping = index_templates["index_templates"][0]["index_template"][
                "template"
            ]["mappings"]
            if not current_mapping == ES_COLLECTIONS_MAPPINGS:
                logger.info("Collections index mappings are outdated, reindexing...")
                # update index templates first
                await create_index_templates()
                _alias = await client.indices.get_alias(name=COLLECTIONS_INDEX)
                old_collection_index = list(_alias.keys())[0]
                suffix = f"{int(old_collection_index.split('-')[-1]) + 1:06d}"
                new_collection_index = f"{COLLECTIONS_INDEX}-{suffix}"
                await client.reindex(
                    body={
                        "source": {"index": old_collection_index},
                        "dest": {"index": new_collection_index},
                    }
                )
                # move the alias
                await client.indices.update_aliases(
                    body={
                        "actions": [
                            {
                                "remove": {
                                    "index": old_collection_index,
                                    "alias": COLLECTIONS_INDEX,
                                }
                            },
                            {
                                "add": {
                                    "index": new_collection_index,
                                    "alias": COLLECTIONS_INDEX,
                                }
                            },
                        ]
                    }
                )


async def ensure_collection_index() -> None:
    """Create the collections index, unless it (or an alias with that name) exists."""
    async with AsyncOpensearchSettings().create_client as client:
        if await client.indices.exists(index=COLLECTIONS_INDEX):
            return
        index = f"{COLLECTIONS_INDEX}-000001"
        logger.info("Creating collections index %s", index)
        await client.indices.create(
            index=index,
            body={
                "aliases": {COLLECTIONS_INDEX: {}},
                "mappings": ES_COLLECTIONS_MAPPINGS,
            },
        )
