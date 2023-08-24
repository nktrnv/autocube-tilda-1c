import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from loguru import logger
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

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
            self, save_to: Path | str, filename_format: str,
            products: Sequence[Product]
    ):
        self._filepath = None
        self._is_empty_file = None
        self._save_to = Path(save_to)
        self._filename_format = filename_format
        self._products = products

        self._characteristic_names = self._get_characteristic_names()
        self._fieldnames = [
            BRAND_COLUMN, SKU_COLUMN, CATEGORY_COLUMN, TITLE_COLUMN,
            DESCRIPTION_COLUMN, TEXT_COLUMN, PHOTO_COLUMN, PRICE_COLUMN,
            QUANTITY_COLUMN, OLD_PRICE_COLUMN, EXTERNAL_ID_COLUMN
        ]
        self._fieldnames += self._characteristic_names

    @property
    def filepath(self):
        return self._filepath

    def create_file(self):
        current_datetime = datetime.now().strftime("%d_%m_%Y-%H_%M_%S")
        filename = self._filename_format.format(datetime=current_datetime)
        self._filepath = self._save_to / filename

        logger.info(f"Start creating a csv file {self._filepath}")

        rows = map(self._get_product_csv_dict_row, self._products)
        self._write_file(self._filepath, rows)

        logger.info(f"Csv file {self._filepath} was created successfully")

    def _write_file(self, path: Path, rows: Iterable[dict]):
        with path.open(mode="w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=self._fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

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
            project_id: str, selenium_timeout: float,
            file_uploading_timeout: float
    ):
        self._email = email
        self._password = password
        self._project_id = project_id
        self._filepath = Path(filepath)
        self._selenium_timeout = selenium_timeout
        self._file_uploading_timeout = file_uploading_timeout

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        self._driver = webdriver.Chrome(options=chrome_options)

        self._driver.implicitly_wait(self._selenium_timeout)

    def upload_file(self):
        try:
            self._login_to_tilda()
        except TimeoutException:
            logger.error("Error while logging in to the Tilda website. A "
                         "captcha or an incorrect login or password was "
                         "encountered.")
        else:
            self._upload_file()

    def _login_to_tilda(self):
        logger.info("Start to login to Tilda website.")

        self._driver.get("https://tilda.cc/login")

        email_input = self._driver.find_element(By.ID, "email")
        email_input.send_keys(self._email)

        password_input = self._driver.find_element(By.ID, "password")
        password_input.send_keys(self._password)

        password_input.send_keys(Keys.ENTER)

        wait = WebDriverWait(self._driver, self._selenium_timeout)
        wait.until(expected_conditions.url_to_be("https://tilda.cc/projects/"))

        logger.info("Successfully logged in to the Tilda website.")

    def _upload_file(self):
        logger.info(f"Start uploading a csv file {self._filepath.name} to "
                    f"Tilda.")

        self._driver.get(
            f"https://store.tilda.cc/store/?projectid={self._project_id}")

        self._driver.execute_script(f"tstore_start_import('csv')")

        select_file_button = self._driver.find_element(
            By.CLASS_NAME, "js-import-load-file-btn")
        select_file_button.click()

        hidden_file_input = self._driver.find_element(
            By.CSS_SELECTOR, "input[type=\"file\"]"
        )
        hidden_file_input.send_keys(str(self._filepath))

        self._driver.execute_script(
            "document.querySelector(`.js-import-load-data`).classList"
            ".remove(`disabled`)"
        )

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

        try:
            wait.until(expected_conditions.visibility_of_element_located(
                results_element_locator))
        except TimeoutException:
            logger.error(f"Exceeded the timeout for uploading a csv file "
                         f"{self._filepath.name} to the Tilda.")

        logger.info(f"Csv file {self._filepath.name} successfully uploaded to "
                    f"Tilda.")
