from copy import deepcopy
from http import HTTPStatus
from typing import Callable, Iterable, Self, Sequence

import requests
from requests.auth import HTTPBasicAuth

from src.entities import Folder, Product

KEY_FIELD = "Ref_Key"
PARENT_KEY_FIELD = "Parent_Key"
IS_FOLDER_FIELD = "IsFolder"
FOLDER_NAME_FIELD = "Description"

NULL_PARENT_KEY = "00000000-0000-0000-0000-000000000000"


class OData1CEntities:
    def __init__(self, entities: Sequence[dict] | None):
        self._entities = entities

    @property
    def entities(self):
        return self._entities

    def expand_with(
            self,
            other_response: Self,
            by: Callable[[Self, Self], bool],
            key: str
    ) -> Self:
        entity_should_be_expanded = by
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

    def get_entities(self, entity: str, select: Iterable[str] | None = None) -> OData1CEntities | None:
        params = {"$format": "json"}
        if select is not None:
            params["$select"] = ",".join(select)

        response = requests.get(
            self._odata_url + entity, auth=self._auth, params=params)

        if response.status_code != HTTPStatus.OK:
            return None

        entities = response.json()["value"]
        return OData1CEntities(entities)


class OData1CProductsMapper:
    def __init__(
            self, entities: OData1CEntities,
            map_single_product: Callable[
                [dict, Sequence[Folder]], Product | None]
    ):
        self._products = entities.entities
        self._map_single_product = map_single_product

    def map_products(self) -> Sequence[Product]:
        return self._get_products_in_folder()

    def _get_products_in_folder(
            self,
            folder_key: str = NULL_PARENT_KEY,
            parent_folders: list[Folder] | None = None,
            nesting_level: int = 0
    ) -> Sequence[Product]:
        if parent_folders is None:
            parent_folders = []

        products = []

        for item in self._products:
            parent_key = item[PARENT_KEY_FIELD]
            if parent_key == folder_key:
                is_folder = item[IS_FOLDER_FIELD]
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
            parent_folders: list[Folder], nesting_level: int) -> Sequence[Product]:
        key = item[KEY_FIELD]
        folder_name = item[FOLDER_NAME_FIELD]
        folder = Folder(folder_name, nesting_level)
        parent_folders += [folder]
        nesting_level += 1
        products = self._get_products_in_folder(
            key, parent_folders, nesting_level)
        return products

    def _process_product(
            self, item: dict, parent_folders: Sequence[Folder]) -> Sequence[Product]:
        product = self._map_single_product(item, parent_folders)
        if product is None:
            return []
        return [product]

