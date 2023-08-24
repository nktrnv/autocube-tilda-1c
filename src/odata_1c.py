from copy import deepcopy
from typing import Callable, Iterable, Self, Sequence

import requests
from loguru import logger
from requests.auth import HTTPBasicAuth

from src.entities import Folder, Product


class OData1CEntities:
    def __init__(self, entities: Sequence[dict] | None):
        self._entities = entities

    @property
    def entities(self):
        return self._entities

    def expand_with(
            self,
            other_response: Self,
            expand_condition: Callable[[Self, Self], bool],
            key: str
    ) -> Self:
        entity_should_be_expanded = expand_condition
        expanded_entities = deepcopy(self._entities)

        for entity in expanded_entities:
            entity[key] = []

            for other_entity in other_response._entities:
                if entity_should_be_expanded(entity, other_entity):
                    entity[key].append(other_entity)

        return OData1CEntities(expanded_entities)


class OData1CClient:
    def __init__(self, odata_url: str, username: str, password: str):
        if not odata_url.endswith("/"):
            odata_url += "/"
        self._odata_url = odata_url
        self._auth = HTTPBasicAuth(
            username.encode("utf-8"), password.encode("utf-8"))

    def get_entities(
            self, entity_name: str, select: Iterable[str] | None = None
    ) -> OData1CEntities | None:
        logger.info(f"Getting the entity {entity_name} using OData")

        params = {"$format": "json"}
        if select is not None:
            params["$select"] = ",".join(select)

        response = requests.get(
            self._odata_url + entity_name, auth=self._auth, params=params)

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            logger.error(f"Failed to get the entity {entity_name} using OData")
            raise error

        entities = response.json()["value"]

        logger.info(f"The entity {entity_name} was successfully retrieved "
                    f"using OData")

        return OData1CEntities(entities)


class OData1CMapper:
    def __init__(
            self,
            entities: OData1CEntities,
            map_single_product: Callable[
                [dict, Sequence[Folder]], Product | None],
            key_field: str = "Ref_Key",
            parent_key_field: str = "Parent_Key",
            is_folder_field: str = "IsFolder",
            folder_name_field: str = "Description",
            null_parent_key: str = "00000000-0000-0000-0000-000000000000"
    ):
        self._products = entities.entities
        self._map_single_product = map_single_product
        self._key_field = key_field
        self._parent_key_field = parent_key_field
        self._is_folder_field = is_folder_field
        self._folder_name_field = folder_name_field
        self._null_parent_key = null_parent_key

    def map_products(self) -> Sequence[Product]:
        return self._get_products_in_folder()

    def _get_products_in_folder(
            self,
            folder_key: str | None = None,
            parent_folders: list[Folder] | None = None,
            nesting_level: int = 0
    ) -> Sequence[Product]:
        if folder_key is None:
            folder_key = self._null_parent_key

        if parent_folders is None:
            parent_folders = []

        products = []

        for item in self._products:
            parent_key = item[self._parent_key_field]
            if parent_key == folder_key:
                is_folder = item[self._is_folder_field]
                copied_parent_folders = deepcopy(parent_folders)
                if is_folder:
                    products += self._process_folder(
                        item, copied_parent_folders, nesting_level)
                else:
                    products += self._process_product(
                        item, copied_parent_folders)

        return products

    def _process_folder(
            self, item: dict,
            parent_folders: list[Folder],
            nesting_level: int
    ) -> Sequence[Product]:
        key = item[self._key_field]
        folder_name = item[self._folder_name_field]
        folder = Folder(folder_name, nesting_level)
        parent_folders += [folder]
        nesting_level += 1
        products = self._get_products_in_folder(
            key, parent_folders, nesting_level)
        return products

    def _process_product(
            self, item: dict, parent_folders: Sequence[Folder]
    ) -> Sequence[Product]:
        product = self._map_single_product(item, parent_folders)
        if product is None:
            return []
        return [product]
