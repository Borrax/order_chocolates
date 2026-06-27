"""
order_chocolates.py

Orders "Шоколад Lindt Excellence тъмен 100 гр" from onegift.bg.

Usage:
    python3 order_chocolates.py [amount]

Arguments:
    amount  Number of chocolates to order (default: 10)

Checkout info is read from customer_info.json (gitignored).
Copy customer_info.example.json -> customer_info.json and fill in your details.
"""

import argparse
import json
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

PRODUCT_URL = "https://www.onegift.bg/productbg/9"
CART_URL = "https://www.onegift.bg/cartbg/"
CHECKOUT_URL = "https://www.onegift.bg/checkoutbg/"
CUSTOMER_INFO_FILE = os.path.join(os.path.dirname(__file__), "customer_info.json")
DEFAULT_AMOUNT = 10
WAIT_TIMEOUT = 15


def load_customer_info():
    if not os.path.exists(CUSTOMER_INFO_FILE):
        print(
            f"ERROR: {CUSTOMER_INFO_FILE} not found.\n"
            "Copy customer_info.example.json -> customer_info.json and fill in your details."
        )
        sys.exit(1)
    with open(CUSTOMER_INFO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    driver = webdriver.Firefox(options=opts)
    driver.set_window_size(1280, 900)
    return driver


def dismiss_cookie_banner(driver, wait):
    try:
        btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.cc-dismiss, .cc-btn.cc-dismiss")))
        btn.click()
    except Exception:
        pass


def add_to_cart(driver, wait, amount):
    print(f"Opening product page...")
    driver.get(PRODUCT_URL)
    dismiss_cookie_banner(driver, wait)

    qty_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='quantity']")))
    qty_input.clear()
    qty_input.send_keys(str(amount))

    add_btn = driver.find_element(By.ID, "buttonAddToCart")
    add_btn.click()
    print(f"Added {amount} chocolates to cart.")
    time.sleep(2)


def set_field(driver, name, value):
    if not value:
        return
    try:
        el = driver.find_element(By.NAME, name)
        tag = el.tag_name.lower()
        if tag == "select":
            sel = Select(el)
            sel.select_by_value(str(value))
        else:
            el.clear()
            el.send_keys(str(value))
    except Exception as e:
        print(f"  Warning: could not set field '{name}': {e}")


def fill_checkout(driver, wait, info):
    print("Navigating to checkout...")
    driver.get(CHECKOUT_URL)
    wait.until(EC.presence_of_element_located((By.ID, "buttonCheckout")))
    dismiss_cookie_banner(driver, wait)

    # Payment type radio
    payment_id = info.get("payment_type_id", "1")
    try:
        radio = driver.find_element(By.CSS_SELECTOR, f"input[name='payment_type_id'][value='{payment_id}']")
        if not radio.is_selected():
            driver.execute_script("arguments[0].click();", radio)
    except Exception as e:
        print(f"  Warning: could not select payment type: {e}")

    # Billing fields
    for field in ["billing_name", "billing_family_name", "billing_phone", "billing_email",
                  "billing_address_line_1", "billing_address_line_2", "billing_postcode"]:
        set_field(driver, field, info.get(field, ""))

    # Delivery type dropdown
    delivery_type = info.get("delivery_type_id", "1")
    try:
        sel = Select(driver.find_element(By.NAME, "delivery_type_id"))
        sel.select_by_value(str(delivery_type))
        time.sleep(1)  # wait for dependent fields to appear
    except Exception as e:
        print(f"  Warning: could not set delivery type: {e}")

    # Delivery region / city dropdowns (if set in info)
    for field in ["delivery_region", "delivery_city"]:
        val = info.get(field, "")
        if val:
            set_field(driver, field, val)
            time.sleep(0.5)

    # Delivery contact & address fields
    for field in ["delivery_name", "delivery_family_name", "delivery_phone",
                  "delivery_address_line_1", "delivery_address_line_2", "delivery_postcode"]:
        set_field(driver, field, info.get(field, ""))

    # Comments (only if present)
    comments = info.get("user_comments", "")
    if comments:
        try:
            cb = driver.find_element(By.ID, "isUserComments")
            if not cb.is_selected():
                cb.click()
            time.sleep(0.3)
        except Exception:
            pass
        set_field(driver, "user_comments", comments)

    # Accept the two terms checkboxes
    for cb_id in ["agree_terms", "agree_terms_gdpr"]:
        try:
            cb = driver.find_element(By.ID, cb_id)
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        except Exception as e:
            print(f"  Warning: could not tick {cb_id}: {e}")

    print("Form filled. Submitting order...")
    submit = driver.find_element(By.ID, "buttonCheckout")
    submit.click()
    time.sleep(3)
    print(f"Order submitted. Final URL: {driver.current_url}")


def main():
    parser = argparse.ArgumentParser(description="Order Lindt chocolates from onegift.bg")
    parser.add_argument("amount", nargs="?", type=int, default=DEFAULT_AMOUNT,
                        help=f"Number of chocolates to order (default: {DEFAULT_AMOUNT})")
    args = parser.parse_args()

    if args.amount <= 0:
        print("ERROR: Amount must be a positive integer.")
        sys.exit(1)

    info = load_customer_info()
    driver = make_driver()
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        add_to_cart(driver, wait, args.amount)
        fill_checkout(driver, wait, info)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
