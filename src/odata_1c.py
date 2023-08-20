import abc
from typing import Sequence, Callable

from src.entities import Product, Folder

KEY_FIELD = "Ref_Key"
PARENT_KEY_FIELD = "Parent_Key"
IS_FOLDER_FIELD = "IsFolder"
FOLDER_NAME_FIELD = "Description"

NULL_PARENT_KEY = "00000000-0000-0000-0000-000000000000"

MapSingleProduct = Callable[[dict, Sequence[Folder]], Product | None]


class OData1CProductsMapper(abc.ABC):
    def __init__(
            self, products: Sequence[dict],
            map_single_product: MapSingleProduct
    ):
        self._products = products
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
                if is_folder:
                    products += self._process_folder(
                        item, parent_folders, nesting_level)
                else:
                    products += self._process_product(item, parent_folders)

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

