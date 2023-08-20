import csv
from pathlib import Path
from typing import Sequence

from src.entities import Product

BRAND_COLUMN = "Brand"
SKU_COLUMN = "SKU"
CATEGORY_COLUMN = "Category"
TITLE_COLUMN = "Title"
DESCRIPTION_COLUMN = "Description"
TEXT_COLUMN = "Text"
PHOTO_COLUMN = "Photo"
PRICE_COLUMN = "Price"
QUANTITY_COLUMN = "Quantity"
OLD_PRICE_COLUMN = "Price OLD"
EXTERNAL_ID_COLUMN = "External ID"
CHARACTERISTIC_COLUMN = "Characteristic"


class TildaCsvFileManager:
    def __init__(self, filepath: Path, products: Sequence[Product]):
        self.filepath = filepath
        self._products = products
        self._characteristic_names = self._get_characteristic_names()

    def create_file(self):
        fieldnames = [
            BRAND_COLUMN, SKU_COLUMN, CATEGORY_COLUMN, TITLE_COLUMN,
            DESCRIPTION_COLUMN, TEXT_COLUMN, PHOTO_COLUMN, PRICE_COLUMN,
            QUANTITY_COLUMN, OLD_PRICE_COLUMN, EXTERNAL_ID_COLUMN
        ]
        fieldnames += self._characteristic_names

        with self.filepath.open("w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in self._products:
                csv_dict_row = self._get_product_csv_dict_row(product)
                writer.writerow(csv_dict_row)

    def remove_file(self):
        self.filepath.unlink()

    def _get_characteristic_names(self) -> Sequence[str]:
        characteristic_names = set()
        for product in self._products:
            characteristics = product.characteristics
            for characteristic in characteristics:
                characteristic_names.update(
                    f"{CHARACTERISTIC_COLUMN}:{characteristic.name}")
        return list(characteristic_names)

    def _get_product_csv_dict_row(
            self, product: Product) -> dict[str, str | float | int | None]:
        csv_dict_row = {
            BRAND_COLUMN: product.brand,
            SKU_COLUMN: product.sku,
            CATEGORY_COLUMN: ";".join(product.categories),
            TITLE_COLUMN: product.title,
            DESCRIPTION_COLUMN: product.description,
            TEXT_COLUMN: product.text,
            PHOTO_COLUMN: product.image_url,
            PRICE_COLUMN: product.price,
            QUANTITY_COLUMN: product.quantity,
            OLD_PRICE_COLUMN: product.old_price,
            EXTERNAL_ID_COLUMN: product.external_id
        }

        characteristics = dict.fromkeys(self._characteristic_names, None)
        for characteristic in product.characteristics:
            characteristics[characteristic.name] = characteristic.value
        csv_dict_row.update(characteristics)

        return csv_dict_row
