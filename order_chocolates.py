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
    # On Linux with snap Firefox the wrapper script isn't a real binary;
    # point Selenium at the real executable. On Windows/macOS skip this.
    snap_firefox = "/snap/firefox/current/usr/lib/firefox/firefox"
    if os.path.exists(snap_firefox):
        opts.binary_location = snap_firefox
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


def select2_set(driver, name, value):
    """Set a Select2 dropdown: update Select2 display AND fire plain change for site listeners."""
    driver.execute_script(
        """
        jQuery('select[name="' + arguments[0] + '"]')
            .val(arguments[1])
            .trigger('change.select2')
            .trigger('change');
        """,
        name, str(value)
    )


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
    # Note: the checkout JS validation reads billing_region, billing_city,
    # billing_address_line_1 and billing_postcode for delivery validation too.
    # So we fill billing address fields with the delivery address values.
    for field in ["billing_name", "billing_family_name", "billing_phone", "billing_email"]:
        val = info.get(field, "")
        if val:
            js_set(driver, field, val)

    # Mirror delivery address into billing address fields (required by site's JS validation)
    addr_map = {
        "billing_address_line_1": info.get("delivery_address_line_1", "") or info.get("billing_address_line_1", ""),
        "billing_address_line_2": info.get("delivery_address_line_2", "") or info.get("billing_address_line_2", ""),
        "billing_postcode":       info.get("delivery_postcode", "") or info.get("billing_postcode", ""),
    }
    for field, val in addr_map.items():
        if val:
            js_set(driver, field, val)

    # Set all delivery dropdowns atomically via JS — no events fired until all values
    # are in place, because each select's change handler resets sibling selects.
    delivery_type = info.get("delivery_type_id", "1")
    delivery_region = info.get("delivery_region", "")
    delivery_city = info.get("delivery_city", "")

    print(f"  Setting delivery type={delivery_type} region={delivery_region} city={delivery_city}...")

    if delivery_region:
        # Pre-populate city options via AJAX, then set all three values silently
        driver.execute_script(
            """
            var deliveryType = arguments[0];
            var deliveryRegion = arguments[1];
            var deliveryCity = arguments[2];

            // Set delivery type and region silently (no change events — handlers reset siblings)
            jQuery('select[name="delivery_type_id"]').val(deliveryType);
            jQuery('select[name="delivery_region"]').val(deliveryRegion);

            // Load city options via AJAX, then set city, then fire the delivery type change
            jQuery.ajax({
                type: 'POST',
                url: '/get-cities',
                data: 'region=' + deliveryRegion,
                dataType: 'json',
                success: function(response) {
                    var $city = jQuery('select[name="delivery_city"]');
                    $city.empty().append('<option value="">Моля изберете Град</option>');
                    jQuery.each(response, function(i, item) {
                        $city.append('<option value="' + item.id + '">' + item.city_type + ' ' + item.name + '</option>');
                    });
                    $city.val(deliveryCity);
                    // Also populate billing selects — JS validation and server read from those
                    var $billingRegion = jQuery('select[name="billing_region"]');
                    var $billingCity = jQuery('select[name="billing_city"]');
                    $billingRegion.val(deliveryRegion);
                    // Copy city options into billing_city and set the same value
                    $billingCity.empty().append('<option value="">Моля изберете Град</option>');
                    jQuery.each(response, function(i, item) {
                        $billingCity.append('<option value="' + item.id + '">' + item.city_type + ' ' + item.name + '</option>');
                    });
                    $billingCity.val(deliveryCity);
                    // Fire delivery_type change last — it shows address section but resets region/city
                    // We set region/city again immediately after to counteract
                    jQuery('select[name="delivery_type_id"]').trigger('change.select2').trigger('change');
                    jQuery('select[name="delivery_region"]').val(deliveryRegion);
                    $city.val(deliveryCity);
                    window._deliveryReady = true;
                }
            });
            """,
            str(delivery_type), str(delivery_region), str(delivery_city)
        )
        print("  Waiting for city AJAX and delivery setup...")
        wait.until(lambda d: d.execute_script("return window._deliveryReady === true;"))
        # slideDown animation runs for ~400ms after the change event; let it finish,
        # then re-assert region and city which get cleared by the re-init inside the handler
        time.sleep(0.6)
        driver.execute_script(
            """
            jQuery('select[name="delivery_region"]').val(arguments[0]);
            jQuery('select[name="delivery_city"]').val(arguments[1]);
            jQuery('select[name="billing_region"]').val(arguments[0]);
            jQuery('select[name="billing_city"]').val(arguments[1]);
            """,
            str(delivery_region), str(delivery_city)
        )
        # Verify billing_city actually took (options must exist in the select)
        billing_city_val = driver.execute_script(
            "return jQuery('select[name=\"billing_city\"]').val();"
        )
        if not billing_city_val:
            # Options may have been cleared by the re-init; copy them from delivery_city select
            driver.execute_script(
                """
                var $src = jQuery('select[name="delivery_city"]');
                var $dst = jQuery('select[name="billing_city"]');
                $dst.empty();
                $src.find('option').each(function() {
                    $dst.append(jQuery(this).clone());
                });
                $dst.val(arguments[0]);
                """,
                str(delivery_city)
            )
    else:
        select2_set(driver, "delivery_type_id", delivery_type)
        time.sleep(1)

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

    # Debug: read back actual values from the DOM
    debug = driver.execute_script("""
        return {
            delivery_type: document.querySelector('select[name="delivery_type_id"]').value,
            delivery_region: document.querySelector('select[name="delivery_region"]').value,
            billing_region: document.querySelector('select[name="billing_region"]').value,
            delivery_city: document.querySelector('select[name="delivery_city"]').value,
            billing_city: document.querySelector('select[name="billing_city"]').value,
            address1: document.querySelector('input[name="delivery_address_line_1"]').value,
            billing_address1: document.querySelector('input[name="billing_address_line_1"]').value,
            postcode: document.querySelector('input[name="delivery_postcode"]').value,
            billing_postcode: document.querySelector('input[name="billing_postcode"]').value,
        };
    """)
    print(f"  DOM values before screenshot: {debug}")

    # --- Submit (JS click to bypass any overlapping chat widget iframes) ---
    print("Submitting order...")
    driver.execute_script("document.getElementById('buttonCheckout').click();")
    time.sleep(3)
    print(f"Order submitted. Final URL: {driver.current_url}")

    # Click "ФИНАЛИЗИРАЙ ПОРЪЧКАТА" on the confirmation page to place the order
    try:
        finalize_btn = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button.submitBtn:not(#buttonCheckout), a.submitBtn")
        ))
        driver.execute_script("arguments[0].click();", finalize_btn)
        time.sleep(3)
        print(f"Order finalized. Final URL: {driver.current_url}")
    except Exception as e:
        print(f"  Warning: could not click finalize button: {e}")

    # --- Screenshots (resize after submit so it doesn't interfere with form state) ---
    full_height = driver.execute_script("return document.body.scrollHeight")
    driver.set_window_size(1280, full_height)
    driver.save_screenshot(PRE_SCREENSHOT_PATH)
    print(f"Pre-submit screenshot saved to {PRE_SCREENSHOT_PATH}")

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
