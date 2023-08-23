from pathlib import Path
from typing import Callable, Sequence

import dropbox
from dropbox.sharing import SharedLinkMetadata

from src.entities import Product


class DropboxProductImagesFolder:
    def __init__(
            self, refresh_token: str, app_key: str, app_secret: str,
            dropbox_folder_path: str
    ):
        self._dropbox = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        self._dropbox_folder_path = dropbox_folder_path
        self._image_names = []

    def upload_images(self, dir_path: Path | str):
        self._image_names = self._get_image_names()

        for path in Path(dir_path).iterdir():
            if path.is_file() and path.name not in self._image_names:
                self._upload_image(path)

    def add_image_url_to_products(
            self,
            products: Sequence[Product],
            match: Callable[[Product, str], bool]
    ):
        if not self._image_names:
            self._image_names = self._get_image_names()

        shared_links = self._get_shared_links()

        for product in products:
            for link in shared_links:
                if match(product, link.name):
                    direct_url = link.url.replace(
                        "www.dropbox.com", "dl.dropboxusercontent.com")
                    product.image_url = direct_url

    def _get_image_names(self) -> list[str]:
        image_names = []
        list_folder_result = self._dropbox.files_list_folder(
            self._dropbox_folder_path)

        while True:
            for entry in list_folder_result.entries:
                image_names.append(entry.name)

            if not list_folder_result.has_more:
                break

            list_folder_result = self._dropbox.files_list_folder_continue(
                list_folder_result.cursor)

        return image_names

    def _upload_image(self, path: Path):
        image_bytes = path.read_bytes()
        dropbox_image_path = f"{self._dropbox_folder_path}/{path.name}"
        self._dropbox.files_upload(image_bytes, dropbox_image_path)
        self._image_names.append(path.name)
        self._dropbox.sharing_create_shared_link_with_settings(
            dropbox_image_path)

    def _get_shared_links(self) -> Sequence[SharedLinkMetadata]:
        links = []
        list_shared_links_result = self._dropbox.sharing_list_shared_links(
            direct_only=True)

        while True:
            for link in list_shared_links_result.links:
                expected_path = f"{self._dropbox_folder_path}/{link.name}"
                if expected_path.lower() == link.path_lower:
                    links.append(link)

            if not list_shared_links_result.has_more:
                break

            list_shared_links_result = self._dropbox.sharing_list_shared_links(
                cursor=list_shared_links_result.cursor, direct_only=True)

        return links
