from pathlib import Path
from typing import Callable, Sequence

import dropbox
from dropbox.exceptions import ApiError
from loguru import logger

from src.entities import Product, ProductWithImage


class ImagesFolder:
    def __init__(
            self,
            folder_path: Path | str,
            products: Sequence[Product],
            default_image_name: str,
            match: Callable[[Product, str], bool]
    ):
        self._folder_path = Path(folder_path)
        self._products = products
        self._default_image_path = self._folder_path / default_image_name
        self._match = match
        self._images = []

        for path in self._folder_path.iterdir():
            if path.is_file() and path.suffix.lower() in [".jpg", ".png"]:
                self._images.append(path)
            else:
                logger.warning(f"Object of the file system with name "
                               f"{path.name} located within the folder of "
                               f"images is not a file or it is not JPG or PNG "
                               f"format.")

        for image in self._images:
            matched_products = list(filter(
                lambda product: self._match(product, image.stem),
                self._products
            ))
            if len(matched_products) == 0:
                logger.warning(f"Image file {image.name} is not used.")

    def get_products_with_images(self) -> Sequence[ProductWithImage]:
        products_with_images = []
        for product in self._products:
            product_with_image = self._get_product_with_image(product)
            products_with_images.append(product_with_image)

        return products_with_images

    def _get_product_with_image(self, product: Product) -> ProductWithImage:
        for image in self._images:
            if self._match(product, image.stem):
                return ProductWithImage(product, image)
        return ProductWithImage(product, self._default_image_path)


class DropboxImages:
    def __init__(
            self,
            refresh_token: str,
            app_key: str,
            app_secret: str,
            dropbox_folder_path: str,
            products_with_images: Sequence[ProductWithImage],
            default_image_path: Path | str
    ):
        self._dropbox = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        self._dropbox_folder_path = dropbox_folder_path
        self._products_with_images = products_with_images
        self._uploaded_images = []
        self._default_image_path = Path(default_image_path)
        self._default_image_url = self._upload_image(self._default_image_path)

    def get_products_with_image_urls(self) -> Sequence[Product]:
        products = []
        for product_with_image in self._products_with_images:
            product = product_with_image.product
            image_path = product_with_image.image_path

            if (image_path == self._default_image_path and
                    product.image_url is not None):
                product.image_url = self._default_image_url
            else:
                product.image_url = self._upload_image(image_path)

            products.append(product)

        return products

    def delete_uploaded_images(self):
        for uploaded_image in self._uploaded_images:
            self._delete_image(uploaded_image)
        self._uploaded_images.clear()

    def _upload_image(self, path: Path) -> str:
        dropbox_image_path = f"{self._dropbox_folder_path}/{path.name}"
        logger.info(f"Uploading the file {dropbox_image_path} to Dropbox.")
        image_bytes = path.read_bytes()
        self._dropbox.files_upload(image_bytes, dropbox_image_path)
        self._uploaded_images.append(dropbox_image_path)
        logger.info(f"File {dropbox_image_path} was successfully uploaded to "
                    f"Dropbox.")
        return self._get_direct_shared_link_url(dropbox_image_path)

    def _get_direct_shared_link_url(self, dropbox_image_path: str) -> str:
        try:
            logger.info(f"Trying to create shared link for "
                        f"{dropbox_image_path}")
            url = self._dropbox.sharing_create_shared_link_with_settings(
                dropbox_image_path).url
            logger.info(f"Shared link for {dropbox_image_path} was "
                        f"successfully created and retrieved.")
        except ApiError:
            logger.info(f"Shared link for {dropbox_image_path} already exists."
                        f"Trying to get shared link.")
            url = self._dropbox.sharing_list_shared_links(
                dropbox_image_path, direct_only=True).links[0].url
            logger.info(f"Shared link for {dropbox_image_path} was "
                        f"successfully retrieved.")
        direct_url = url.replace(
            "www.dropbox.com", "dl.dropboxusercontent.com")
        return direct_url

    def _delete_image(self, dropbox_image_path: str):
        logger.info(f"Deleting the file {dropbox_image_path} from Dropbox.")
        self._dropbox.files_delete(dropbox_image_path)
        logger.info(f"File {dropbox_image_path} was successfully deleted from "
                    f"Dropbox.")
