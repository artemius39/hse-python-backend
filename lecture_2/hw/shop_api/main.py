from collections import Counter
from http import HTTPStatus
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    item_ids: List[int]


class CartResponse(BaseModel):
    id: int
    items: List[CartItem]
    price: float


class CartCreatedResponse(BaseModel):
    id: int


class CreateItemRequest(BaseModel):
    name: str
    price: float


class UpdateItemRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "forbid"


app = FastAPI(title="Shop API")

items_map: Dict[int, Item] = {}
cart_map: Dict[int, Cart] = {}


def build_cart_item(id: int, count: int) -> CartItem:
    item = items_map.get(id)
    return CartItem(
        id=id,
        name=item.name,
        quantity=count,
        available=not item.deleted,
    )


def build_cart_response(cart: Cart) -> CartResponse:
    counter = Counter(cart.item_ids)
    items = [build_cart_item(id, count) for id, count in counter.items()]
    price = sum(item.quantity * items_map[item.id].price for item in items if item.available)
    return CartResponse(
        id=cart.id,
        items=items,
        price=price,
    )


def build_item(id, request):
    return Item(
        id=id,
        name=request.name,
        price=request.price,
        deleted=False,
    )


def assert_cart_exists(cart_id):
    if cart_id not in cart_map:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Cart with id={cart_id} not found")


def assert_item_exists(id):
    if id not in items_map:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id={id} not found")


def apply_offset_limit(data, offset, limit):
    return data[offset:min(len(data), offset + limit)]


@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    id = len(items_map) + 1
    cart = Cart(
        id=id,
        item_ids=[],
    )
    cart_map[id] = cart
    response.headers["location"] = f"/cart/{id}"
    return CartCreatedResponse(id=id).model_dump()


@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(request: CreateItemRequest):
    id = len(items_map) + 1
    item = build_item(id, request)
    items_map[id] = item
    return item.model_dump()


@app.get("/cart/{id}")
def get_cart(id: int):
    assert_cart_exists(id)
    return build_cart_response(cart_map[id])


@app.get("/item/{id}")
def get_item(id: int):
    assert_item_exists(id)
    item = items_map[id]
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id={id} was deleted")
    return item


@app.get("/cart")
def get_carts(
        offset: Optional[int] = Query(0, ge=0),
        limit: Optional[int] = Query(10, gt=0),
        min_price: Optional[float] = Query(default=None, ge=0),
        max_price: Optional[float] = Query(default=None, ge=0),
        min_quantity: Optional[int] = Query(default=None, ge=0),
        max_quantity: Optional[int] = Query(default=None, ge=0),
):
    carts = [build_cart_response(cart) for cart in cart_map.values()]
    carts_filtered = [
        cart for cart in carts
        if (min_price is None or cart.price >= min_price) and
           (max_price is None or cart.price <= max_price) and
           (min_quantity is None or sum(item.quantity for item in cart.items) >= min_quantity) and
           (max_quantity is None or sum(item.quantity for item in cart.items) <= max_quantity)
    ]
    return apply_offset_limit(carts_filtered, offset, limit)


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    assert_cart_exists(cart_id)
    assert_item_exists(item_id)
    cart_map[cart_id].item_ids.append(item_id)


@app.get("/item")
def get_items(
        offset: Optional[int] = Query(0, ge=0),
        limit: Optional[int] = Query(10, gt=0),
        min_price: Optional[float] = Query(default=None, gt=0),
        max_price: Optional[float] = Query(default=None, gt=0),
        show_deleted: Optional[bool] = Query(default=True),
):
    items_filtered = [
        item for item in items_map.values()
        if (min_price is None or item.price >= min_price) and
           (max_price is None or item.price <= max_price) and
           (show_deleted or not item.deleted)
    ]
    return apply_offset_limit(items_filtered, offset, limit)


@app.put("/item/{id}")
def put_item(id: int, request: CreateItemRequest):
    assert_item_exists(id)
    item = build_item(id, request)
    items_map[id] = item
    return item


@app.patch("/item/{id}")
def patch_item(
        response: Response,
        id: int,
        request: UpdateItemRequest
):
    assert_item_exists(id)
    item = items_map[id]
    if item.deleted:
        response.status_code = HTTPStatus.NOT_MODIFIED
        return item
    if request.name is not None:
        item.name = request.name
    if request.price is not None:
        item.price = request.price
    return item


@app.delete("/item/{id}")
def delete_item(id: int):
    assert_item_exists(id)
    items_map[id].deleted = True
