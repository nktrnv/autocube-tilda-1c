from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class Characteristic:
    name: str
    value: str


@dataclass(slots=True)
class Product:
    external_id: str
    title: str
    description: str = ""
    text: str = ""
    sku: str = ""
    brand: str = ""
    price: float | None = None
    old_price: float | None = None
    quantity: int | None = None
    image_url: str = ""
    categories: Sequence[str] = field(default_factory=list)
    characteristics: Sequence[Characteristic] = field(default_factory=list)


@dataclass(slots=True)
class ProductWithImage:
    product: Product
    image_path: Path | None = None


@dataclass(slots=True)
class Folder:
    name: str
    nesting_level: int
