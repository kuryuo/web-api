import time
import asyncio
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from sqlmodel import Session
from database import Product

def parse_website(url: str):
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()))
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "catalog-item"))
    )

    list_products = []

    while len(list_products) < 50:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "lxml")
        products = soup.find_all("a", class_="catalog-item")

        if not products:
            break

        for product in products:
            if len(list_products) >= 50:
                break

            name = product.find('div', class_='catalog-item__name').contents[0].strip()
            price = product.find('span', class_='catalog-item__price-span').text.strip() if product.find('span',
                                                                                                         class_='catalog-item__price-span') else None
            list_products.append({"name": name, "price": float(price.replace('₽', '').strip()) if price else 0})

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    driver.quit()
    return list_products

def add_products_to_db(products: list, session: Session):
    for product in products:
        db_product = Product(name=product["name"], price=product["price"])
        session.add(db_product)
    session.commit()

async def background_parser(url: str, session: Session):
    while True:
        print("Data parsing...")
        products = parse_website(url)
        add_products_to_db(products, session)
        await asyncio.sleep(12 * 60 * 60)