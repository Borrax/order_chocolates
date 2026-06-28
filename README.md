# order_chocolates

Orders "Шоколад Lindt Excellence тъмен 100 гр" from onegift.bg via browser automation.

## Setup

```bash
python -m venv .venv
```

Then install dependencies:

- **Windows:** `.venv\Scripts\pip install selenium`
- **Linux/macOS:** `.venv/bin/pip install selenium`

Or simply `pip install selenium` if pip is already in your PATH.

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
| delivery_region / delivery_city | Numeric IDs from the site's dropdowns. Region IDs: 1=Благоевград, 2=Бургас, 3=Варна, 4=Велико Търново, 5=Видин, 6=Враца, 7=Габрово, 8=Добрич, 9=Кърджали, 10=Кюстендил, 11=Ловеч, 12=Монтана, 13=Пазарджик, 14=Перник, 15=Плевен, 16=Пловдив, 17=Разград, 18=Русе, 19=Силистра, 20=Сливен, 21=Смолян, 22=София, 23=София Област, 24=Стара Загора, 25=Търговище, 26=Хасково, 27=Шумен, 28=Ямбол. City IDs are loaded dynamically after region is set — run the script once with `delivery_city: ""` and check the screenshot to see the populated options, then set the right ID. |
| delivery_postcode | Postcode |
| user_comments | Optional order comments |
