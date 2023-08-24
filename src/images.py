from pathlib import Path
from typing import Callable, Sequence

import dropbox

from src.entities import Product, ProductWithImage


class ImagesFolder:
    def __init__(self, folder_path: Path | str):
        self._folder_path = folder_path
        self._images = []
        for path in folder_path.iterdir():
            if path.is_file() and path.suffix.lower() in [".jpg", ".png"]:
                self._images.append(path)

    def get_products_with_images(
            self,
            products: Sequence[Product],
            match: Callable[[Product, str], bool]
    ) -> Sequence[ProductWithImage]:
        products_with_images = []
        for product in products:
            product_with_image = self._get_product_with_image(product, match)
            products_with_images.append(product_with_image)
        return products_with_images

    def _get_product_with_image(
            self,
            product: Product,
            match: Callable[[Product, str], bool]
    ) -> ProductWithImage:
        for image in self._images:
            if match(product, image.stem):
                return ProductWithImage(product, image)
        return ProductWithImage(product)


class DropboxImages:
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
        self._uploaded_images = []

    def get_products_with_image_urls(
            self, products_with_images: Sequence[ProductWithImage]
    ) -> Sequence[Product]:
        products = []
        for product_with_image in products_with_images:
            url = self._upload_image(product_with_image.image_path)
            product = product_with_image.product
            product.image_url = url
            products.append(product)
        return products

    def delete_uploaded_images(self):
        for uploaded_image in self._uploaded_images:
            self._delete_image(uploaded_image)
        self._uploaded_images.clear()

    def _upload_image(self, path: Path) -> str:
        image_bytes = path.read_bytes()
        dropbox_image_path = f"{self._dropbox_folder_path}/{path.name}"
        self._dropbox.files_upload(image_bytes, dropbox_image_path)
        self._uploaded_images.append(dropbox_image_path)
        return self._get_direct_shared_link_url(dropbox_image_path)

    def _get_direct_shared_link_url(self, dropbox_image_path: str) -> str:
        url = self._dropbox.sharing_create_shared_link_with_settings(
            dropbox_image_path).url
        direct_url = url.replace(
            "www.dropbox.com", "dl.dropboxusercontent.com")
        return direct_url

    def _delete_image(self, dropbox_image_path: str):
        self._dropbox.files_delete(dropbox_image_path)

