import csv
from datetime import datetime
from pathlib import Path
from typing import Sequence

from pywinauto import findwindows, keyboard, timings
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from src.config import settings
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
    def __init__(
            self,
            save_to: Path | str,
            filename_format: str, products: Sequence[Product]
    ):
        self._filepath = None
        self._save_to = Path(save_to)
        self._filename_format = filename_format
        self._products = products
        self._characteristic_names = self._get_characteristic_names()

    @property
    def filepath(self):
        return self._filepath

    def create_file(self):
        fieldnames = [
            BRAND_COLUMN, SKU_COLUMN, CATEGORY_COLUMN, TITLE_COLUMN,
            DESCRIPTION_COLUMN, TEXT_COLUMN, PHOTO_COLUMN, PRICE_COLUMN,
            QUANTITY_COLUMN, OLD_PRICE_COLUMN, EXTERNAL_ID_COLUMN
        ]
        fieldnames += self._characteristic_names

        current_datetime = datetime.now().strftime("%d_%m_%Y-%H_%M_%S")
        filename = self._filename_format.format(datetime=current_datetime)
        self._filepath = self._save_to / filename

        with self._filepath.open(
                mode="w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()

            for product in self._products:
                csv_dict_row = self._get_product_csv_dict_row(product)
                writer.writerow(csv_dict_row)

    def remove_file(self):
        self._filepath.unlink()

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


class TildaSeleniumCsvFileUploader:
    def __init__(
            self, filepath: Path | str, email: str, password: str,
            project_id: str, driver: WebDriver, selenium_timeout: float,
            file_uploading_timeout: float
    ):
        self._email = email
        self._password = password
        self._project_id = project_id
        self._filepath = Path(filepath)
        self._driver = driver
        self._selenium_timeout = selenium_timeout
        self._file_uploading_timeout = file_uploading_timeout

        driver.implicitly_wait(self._selenium_timeout)

    def upload_file(self):
        self._login_to_tilda()
        self._upload_file()

    def _login_to_tilda(self):
        self._driver.get("https://tilda.cc/login")

        email_input = self._driver.find_element(By.ID, "email")
        email_input.send_keys(self._email)

        password_input = self._driver.find_element(By.ID, "password")
        password_input.send_keys(self._password)

        password_input.send_keys(Keys.ENTER)

        wait = WebDriverWait(self._driver, self._selenium_timeout)
        wait.until(expected_conditions.url_to_be("https://tilda.cc/projects/"))

    def _upload_file(self):
        self._driver.get(
            f"https://store.tilda.cc/store/?projectid={self._project_id}")

        self._driver.execute_script(
            f"tstore_start_import('csv')")

        select_file_button = self._driver.find_element(
            By.CLASS_NAME, "js-import-load-file-btn")
        select_file_button.click()

        self._select_file()

        submit_file_button = self._driver.find_element(
            By.CLASS_NAME, "js-import-load-data")
        submit_file_button.click()

        submit_import_options_button = self._driver.find_element(
            By.CLASS_NAME, "btn_importcsv_proccess")
        submit_import_options_button.click()

        wait = WebDriverWait(
            self._driver, self._file_uploading_timeout)
        results_element_locator = (
            By.CLASS_NAME, "t-store__import__results")
        wait.until(expected_conditions.visibility_of_element_located(
            results_element_locator))

    def _select_file(self):
        browser = findwindows.find_element(active_only=True)

        try:
            timings.wait_until_passes(
                timeout=settings.selenium_timeout,
                retry_interval=0.5,
                func=lambda: findwindows.find_element(
                    active_only=True, parent=browser),
                exceptions=findwindows.ElementNotFoundError
            )
        except TimeoutError:
            pass
        else:
            filepath = self._filepath.absolute()
            keys = str(filepath) + "{ENTER}"
            keyboard.send_keys(keys, with_spaces=True)
