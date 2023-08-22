from typing import Sequence

from selenium import webdriver

from src.config import settings
from src.dropbox_images import DropboxProductImagesFolder
from src.entities import Folder, Product
from src.odata_1c import OData1CClient, OData1CProductsMapper
from src.tilda import TildaCsvFileManager, TildaSeleniumCsvFileUploader

CSV_FILENAME = "import.csv"


def get_product_brand(folders: Sequence[Folder]) -> str:
    for folder in folders:
        if folder.nesting_level == 1:
            return folder.name
    return ""


def get_product_price(product: dict) -> int | None:
    for price_option in product["Цены"]:
        if price_option["ТипЦены"][0]["Description"] == "Розничная цена":
            return int(price_option["Цена"])


def get_product_quantity(product: dict) -> int:
    if product["Остаток"]:
        return int(product["Остаток"][0]["КоличествоBalance"])
    return 0


def map_single_product(
        product: dict, folders: Sequence[Folder]) -> Product | None:
    if not product["Артикул"]:
        return

    folder_names = [folder.name for folder in folders]
    is_not_part = "Запасные части" not in folder_names
    is_not_foton = "FOTON" not in folder_names
    if is_not_part and is_not_foton:
        return

    return Product(
        external_id=product["Ref_Key"],
        title=product["НаименованиеПолное"],
        sku=product["Артикул"],
        brand=get_product_brand(folders),
        price=get_product_price(product),
        quantity=get_product_quantity(product),
        categories=[
            "Запчасти/Каталог", f"Запчасти/{get_product_brand(folders)}"]
    )


def get_products_from_1c() -> Sequence[Product]:
    odata_client = OData1CClient(
        settings.odata_url, settings.odata_username, settings.odata_password)

    product_entities = odata_client.get_entities(entity_name="Catalog_Номенклатура",
                                                 select=["Ref_Key", "Parent_Key", "IsFolder", "Description",
                                                         "НаименованиеПолное", "Артикул"])

    stock_entities = odata_client.get_entities(entity_name="AccumulationRegister_ОстаткиТоваровКомпании/Balance()",
                                               select=["Номенклатура_Key", "КоличествоBalance"])

    price_entities = odata_client.get_entities(entity_name="InformationRegister_Цены_RecordType/SliceLast()",
                                               select=["Номенклатура_Key", "ТипЦен_Key", "Цена"])

    price_type_entities = odata_client.get_entities(entity_name="Catalog_ТипыЦен", select=["Ref_Key", "Description"])

    prices_extended_with_types = price_entities.expand_with(
        price_type_entities,
        expand_condition=lambda price, price_type:
            price["ТипЦен_Key"] == price_type["Ref_Key"],
        key="ТипЦены"
    )

    extended_product_entities = product_entities.expand_with(
        prices_extended_with_types,
        expand_condition=lambda product, price:
            product["Ref_Key"] == price["Номенклатура_Key"],
        key="Цены"
    ).expand_with(
        stock_entities,
        expand_condition=lambda product, stock:
            product["Ref_Key"] == stock["Номенклатура_Key"],
        key="Остаток"
    )

    return OData1CProductsMapper(
        extended_product_entities, map_single_product).map_products()[:50]


def add_image_url_to_products(
        products: Sequence[Product]) -> Sequence[Product]:
    dropbox_folder = DropboxProductImagesFolder(
        settings.dropbox_refresh_token,
        settings.dropbox_app_key,
        settings.dropbox_app_secret,
        folder_path="/Запчасти"
    )

    dropbox_folder.upload_images_from_file_system_directory(settings.images_directory)

    return dropbox_folder.add_image_url_to_products(
        products,
        match=lambda product, image_name: product.sku + ".jpg" == image_name
    )


def upload_products_to_tilda(products: Sequence[Product]):
    selenium_driver = webdriver.Chrome()
    file_uploader = TildaSeleniumCsvFileUploader(
        CSV_FILENAME, settings.tilda_email, settings.tilda_password,
        settings.tilda_project_id, selenium_driver, settings.selenium_timeout,
        settings.selenium_file_uploading_timeout
    )

    file_manager = TildaCsvFileManager(CSV_FILENAME, products)

    file_manager.create_file()
    file_uploader.upload_file()
    file_manager.remove_file()


def main():
    products = get_products_from_1c()
    products_with_images = add_image_url_to_products(products)
    upload_products_to_tilda(products_with_images)


if __name__ == '__main__':
    main()
