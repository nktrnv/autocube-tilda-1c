from copy import deepcopy
from pathlib import Path
from typing import Callable, Sequence

import dropbox
from dropbox.exceptions import ApiError

from src.entities import Product


class DropboxProductImagesFolder:
    def __init__(
            self, refresh_token: str, app_key: str, app_secret: str,
            folder_path: str
    ):
        self._dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        self._folder_path = folder_path
        self._image_names = self._get_image_names()

    def add_image_url_to_products(
            self,
            products: Sequence[Product],
            match: Callable[[Product, str], bool]
    ) -> Sequence[Product]:
        products = deepcopy(products)
        for product in products:
            for image_name in self._image_names:
                if match(product, image_name):
                    product.image_url = self._get_direct_shared_link(
                        f"{self._folder_path}/{image_name}")
                    break
        return products

    def upload_images_from_file_system_directory(self, dir_path: Path | str):
        for path in Path(dir_path).iterdir():
            if path.is_file():
                data = path.read_bytes()
                path = f"{self._folder_path}/{path.name}"
                self._dbx.files_upload(data, path)

    def _get_image_names(self) -> list[str]:
        image_names = []
        list_folder_result = self._dbx.files_list_folder(self._folder_path)
        while True:
            for entry in list_folder_result.entries:
                image_names.append(entry.name)
            if not list_folder_result.has_more:
                break
            list_folder_result = self._dbx.files_list_folder_continue(
                list_folder_result.cursor)
        return image_names

    def _create_shared_link(self, image_path: str):
        try:
            self._dbx.sharing_create_shared_link_with_settings(image_path)
        except ApiError:
            pass

    def _get_shared_link(self, image_path: str):
        return self._dbx.sharing_list_shared_links(
            image_path, direct_only=True).links[0].url

    def _get_direct_shared_link(self, image_path: str):
        self._create_shared_link(image_path)
        shared_link = self._get_shared_link(image_path)
        direct_shared_link = shared_link.replace(
            "www.dropbox.com", "dl.dropboxusercontent.com")
        return direct_shared_link
