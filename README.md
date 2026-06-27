# order_chocolates

Orders "Шоколад Lindt Excellence тъмен 100 гр" from onegift.bg via browser automation.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install selenium
```

Firefox + geckodriver must be installed (`geckodriver` in PATH).

Copy the example config and fill in your details:

```bash
cp customer_info.example.json customer_info.json
# edit customer_info.json — it is gitignored
```

## Usage

```bash
# Order 10 chocolates (default)
python3 order_chocolates.py

# Order a specific amount
python3 order_chocolates.py 5
```

## customer_info.json fields

| Field | Description |
|---|---|
| billing_name | First name |
| billing_family_name | Last name |
| billing_phone | Phone number |
| billing_email | Email address |
| payment_type_id | 1=Cash on delivery, 3=Card, 4=Bank transfer, 7=Revolut |
| delivery_type_id | 1=Speedy address, 2=Speedy office, 4=Econt office, 5=Econt address |
| delivery_name / delivery_family_name / delivery_phone | Recipient info |
| delivery_address_line_1/2 | Street address (for address delivery) |
| delivery_region / delivery_city | Region/city selects (value IDs from site) |
| delivery_postcode | Postcode |
| user_comments | Optional order comments |
