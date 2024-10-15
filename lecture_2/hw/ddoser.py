from concurrent.futures import ThreadPoolExecutor, as_completed
from string import digits

import requests
from faker import Faker
from faker.generator import random

faker = Faker()


def create_carts():
    for _ in range(500):
        response = requests.post("http://localhost:8000/cart")
        print(response)


def get_carts():
    for _ in range(500):
        response = requests.get(f"http://localhost:8000/cart/{random.choice([1, 100])}")
        print(response)


with ThreadPoolExecutor() as executor:
    futures = {}

    for i in range(15):
        futures[executor.submit(create_carts)] = f"create-user-{i}"

    for future in as_completed(futures):
        print(f"completed {futures[future]}")

    futures = {}

    for _ in range(15):
        futures[executor.submit(get_carts)] = f"get-users-{i}"

    for future in as_completed(futures):
        print(f"completed {futures[future]}")
