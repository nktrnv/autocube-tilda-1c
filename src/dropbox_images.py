from pathlib import Path
from typing import Callable

import dropbox
from dropbox.exceptions import ApiError

from src.entities import Product


class DropboxProductImagesFolder:
    def __init__(
            self, refresh_token: str, app_key: str, app_secret: str,
            dropbox_folder_path: str
    ):
        self._image_names = None
        self._dropbox = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        self._dropbox_folder_path = dropbox_folder_path

    def get_image_url(
            self, product: Product, match: Callable[[Product, str], bool]
    ) -> str | None:
        if self._image_names is None:
            self._image_names = self._get_image_names()

        for image_name in self._image_names:
            if match(product, image_name):
                dropbox_image_path = \
                    f"{self._dropbox_folder_path}/{image_name}"
                return self._get_direct_shared_link(
                    dropbox_image_path)

    def upload_images(self, dir_path: Path | str):
        for path in Path(dir_path).iterdir():
            if path.is_file():
                image_bytes = path.read_bytes()
                dropbox_image_path = f"{self._dropbox_folder_path}/{path.name}"
                self._dropbox.files_upload(image_bytes, dropbox_image_path)
        self._image_names = self._get_image_names()

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

    def _create_shared_link(self, dropbox_image_path: str):
        try:
            self._dropbox.sharing_create_shared_link_with_settings(
                dropbox_image_path)
        except ApiError:
            pass

    def _get_shared_link(self, dropbox_image_path: str):
        return self._dropbox.sharing_list_shared_links(
            dropbox_image_path, direct_only=True).links[0].url

    def _get_direct_shared_link(self, dropbox_image_path: str):
        self._create_shared_link(dropbox_image_path)
        shared_link = self._get_shared_link(dropbox_image_path)
        direct_shared_link = shared_link.replace(
            "www.dropbox.com", "dl.dropboxusercontent.com")
        return direct_shared_link
