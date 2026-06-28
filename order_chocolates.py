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
from selenium.webdriver.support.ui import WebDriverWait

PRODUCT_URL = "https://www.onegift.bg/productbg/9"
CHECKOUT_URL = "https://www.onegift.bg/checkoutbg/"
CUSTOMER_INFO_FILE = os.path.join(os.path.dirname(__file__), "customer_info.json")
SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "order_screenshot.png")
PRE_SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "pre_submit_screenshot.png")
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
        btn = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button.cc-dismiss, .cc-btn.cc-dismiss")))
        btn.click()
    except Exception:
        pass


def js_set(driver, name, value):
    """Set a plain input value via JS and fire input+change events."""
    driver.execute_script(
        """
        var el = document.querySelector('[name="' + arguments[0] + '"]');
        if (el) {
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }
        """,
        name, str(value)
    )


def select2_set(driver, wait, select_name, value):
    """
    Drive a Select2 widget by clicking through its UI.
    Looks up the option text for `value` in the underlying <select>,
    opens the dropdown by clicking the Select2 trigger, then clicks the matching option.
    Returns True on success.
    """
    # Resolve option text from the hidden <select>
    option_text = driver.execute_script(
        """
        var sel = document.querySelector('select[name="' + arguments[0] + '"]');
        if (!sel) return null;
        var opt = Array.from(sel.options).find(function(o) { return o.value == arguments[1]; });
        return opt ? opt.textContent.trim() : null;
        """,
        select_name, str(value)
    )
    if not option_text:
        print(f"  Warning: no option value='{value}' found in select '{select_name}'")
        return False

    # Click the Select2 trigger (the span that sits next to the hidden <select>)
    clicked = driver.execute_script(
        """
        var sel = document.querySelector('select[name="' + arguments[0] + '"]');
        if (!sel) return false;
        // Select2 appends its container right after the <select>
        var next = sel.nextElementSibling;
        if (next && next.classList.contains('select2-container')) {
            var trigger = next.querySelector('.select2-selection');
            if (trigger) { trigger.click(); return true; }
        }
        return false;
        """,
        select_name
    )
    if not clicked:
        print(f"  Warning: could not find Select2 trigger for '{select_name}'")
        return False

    # Wait for the dropdown list to appear
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.select2-results__option')))
    except Exception:
        print(f"  Warning: Select2 dropdown did not open for '{select_name}'")
        return False

    # Click the matching option
    for opt in driver.find_elements(By.CSS_SELECTOR, '.select2-results__option'):
        if opt.text.strip() == option_text:
            opt.click()
            return True

    print(f"  Warning: option '{option_text}' not found in open Select2 dropdown")
    return False


def add_to_cart(driver, wait, amount):
    print("Opening product page...")
    driver.get(PRODUCT_URL)
    dismiss_cookie_banner(driver, wait)

    qty_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='quantity']")))
    qty_input.clear()
    qty_input.send_keys(str(amount))

    driver.find_element(By.ID, "buttonAddToCart").click()
    print(f"Added {amount} chocolates to cart.")
    time.sleep(2)


def fill_checkout(driver, wait, info):
    print("Navigating to checkout...")
    driver.get(CHECKOUT_URL)
    wait.until(EC.presence_of_element_located((By.ID, "buttonCheckout")))
    dismiss_cookie_banner(driver, wait)

    # --- Payment type radio ---
    payment_id = info.get("payment_type_id", "1")
    try:
        radio = driver.find_element(
            By.CSS_SELECTOR, f"input[name='payment_type_id'][value='{payment_id}']")
        if not radio.is_selected():
            driver.execute_script("arguments[0].click();", radio)
    except Exception as e:
        print(f"  Warning: payment type: {e}")

    # --- Billing fields ---
    for field in ["billing_name", "billing_family_name", "billing_phone", "billing_email"]:
        val = info.get(field, "")
        if val:
            js_set(driver, field, val)

    # --- Delivery type (Select2) ---
    delivery_type = info.get("delivery_type_id", "1")
    print(f"  Setting delivery type to {delivery_type}...")
    select2_set(driver, wait, "delivery_type_id", delivery_type)
    time.sleep(1)

    # --- Delivery region (Select2, triggers AJAX city load) ---
    delivery_region = info.get("delivery_region", "")
    if delivery_region:
        print(f"  Setting delivery region to {delivery_region}...")
        select2_set(driver, wait, "delivery_region", delivery_region)
        # Wait for city dropdown to populate
        print("  Waiting for cities to load...")
        try:
            wait.until(lambda d: len(
                d.find_element(By.CSS_SELECTOR, 'select[name="delivery_city"]')
                 .find_elements(By.TAG_NAME, "option")
            ) > 1)
        except Exception:
            print("  Warning: city dropdown did not populate in time")

    # --- Delivery city (Select2) ---
    delivery_city = info.get("delivery_city", "")
    if delivery_city:
        print(f"  Setting delivery city to {delivery_city}...")
        select2_set(driver, wait, "delivery_city", delivery_city)
        time.sleep(0.5)

    # --- Delivery contact + address fields ---
    for field in ["delivery_name", "delivery_family_name", "delivery_phone",
                  "delivery_address_line_1", "delivery_address_line_2", "delivery_postcode"]:
        val = info.get(field, "")
        if val:
            js_set(driver, field, val)

    # --- Optional comment ---
    comments = info.get("user_comments", "")
    if comments:
        try:
            cb = driver.find_element(By.ID, "isUserComments")
            if not cb.is_selected():
                cb.click()
            time.sleep(0.3)
        except Exception:
            pass
        js_set(driver, "user_comments", comments)

    # --- Consent checkboxes ---
    for cb_id in ["agree_terms", "agree_terms_gdpr"]:
        try:
            cb = driver.find_element(By.ID, cb_id)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        except Exception as e:
            print(f"  Warning: checkbox {cb_id}: {e}")

    # --- Pre-submit screenshot (full page height) ---
    full_height = driver.execute_script("return document.body.scrollHeight")
    driver.set_window_size(1280, full_height)
    driver.save_screenshot(PRE_SCREENSHOT_PATH)
    print(f"Pre-submit screenshot saved to {PRE_SCREENSHOT_PATH}")

    # --- Submit ---
    print("Submitting order...")
    driver.find_element(By.ID, "buttonCheckout").click()
    time.sleep(3)
    print(f"Order submitted. Final URL: {driver.current_url}")

    driver.save_screenshot(SCREENSHOT_PATH)
    print(f"Post-submit screenshot saved to {SCREENSHOT_PATH}")


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
