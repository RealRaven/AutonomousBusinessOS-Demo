# presentation/tabs/test_data_tab.py

import random
import tempfile
import uuid
import zipfile
from pathlib import Path
from datetime import datetime

import gradio as gr
from weasyprint import HTML

from application.customer_service import CustomerService
from core.models import Customer


class TestDataTab:
    def __init__(self, customer_service: CustomerService):
        self.service = customer_service

    def get_title(self):
        return "🧪 Test Invoices"

    # -----------------------------
    # DATA POOLS (Texas Legacy Edition)
    # -----------------------------
    COMPANIES = [
        "Lone Star Trust & Heritage Co.", "Trinity River Logistics Inc.",
        "Summit Energy Partners", "Frontier Commerce Group LLC",
        "Alamo Capital Holdings", "Apex Industrial Supply",
        "Brazos Valley Distribution", "Pioneer Tech Systems Ltd.",
        "Red River Land & Cattle Co.", "Cornerstone Office Solutions",
        "Keystone Infrastructure Group", "Midland Petroleum Partners",
        "Guardian Security & Data", "High Plains Agricultural Corp.",
        "Heritage Financial Systems", "Gulf Coast Maritime LLC"
    ]

    PRODUCTS = [
        ("Ergonomic Office Chair", 249.99),
        ("4K UltraWide Monitor 34\"", 799.00),
        ("Wireless Headphones", 199.90),
        ("Mechanical Keyboard", 149.50),
        ("Portable SSD 2TB", 179.99),
        ("Smart Desk Lamp", 89.99),
        ("Laptop Stand", 59.99),
        ("Cloud Backup (1 Year)", 129.00),
        ("Wireless Mouse", 49.90),
        ("Standing Desk", 499.00),
        ("Dual-Monitor Desk Mount", 115.50),
        ("Conference Room Speakerphone", 189.00),
        ("Heavy-Duty Document Shredder", 275.00),
        ("Under-Desk Walking Pad", 349.99),
        ("Uninterruptible Power Supply (UPS)", 159.00)
    ]

    FIRST_NAMES = [
        "James", "John", "William", "Robert", "Michael", "David", 
        "Charles", "Thomas", "Richard", "Joseph", "Daniel", "Matthew",
        "Mary", "Elizabeth", "Sarah", "Emily", "Patricia", "Jennifer", 
        "Linda", "Barbara", "Susan", "Margaret", "Dorothy", "Katherine"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", 
        "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", 
        "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
        "Garcia", "Martinez", "Rodriguez", "Carter", "Clark", "Walker"
    ]

    STREETS = [
        "Main Street", "Commerce Street", "Market Street", "Broadway",
        "Westheimer Road", "Congress Avenue", "Alamo Plaza", "Travis Street",
        "Washington Boulevard", "Bluebonnet Lane", "Oak Street", "Maple Avenue",
        "Pine Street", "Cedar Lane", "Memorial Drive", "Trinity Way",
        "Legacy Drive", "Canyon Ridge Road", "Brazos Street", "Pecos Trail"
    ]

    CITIES = [
        "Fort Worth", "Plano", "Frisco", "McKinney", "The Woodlands", 
        "Tyler", "Midland", "Abilene", "Amarillo", "Lubbock", 
        "Waco", "Houston", "Dallas", "San Antonio", "New Braunfels"
    ]

    # Standard Texas Sales and Use Tax Rate is 6.25%, with local jurisdictions adding up to 2% (totaling 8.25%)
    TAX_RATE = 0.0825

    # -----------------------------
    # RANDOM CUSTOMER GENERATOR
    # -----------------------------
    def generate_random_customer(self, i: int) -> Customer:
        first = random.choice(self.FIRST_NAMES)
        last = random.choice(self.LAST_NAMES)

        name = f"{first} {last}"

        # dynamic company
        if random.random() < 0.5:
            company = random.choice(self.COMPANIES)
        else:
            company = f"{last} {random.choice(['Consulting', 'Solutions', 'Holdings', 'Services'])} LLC"

        email = f"{first.lower()}.{last.lower()}{random.randint(1,99)}@example.com"

        # Realistic US Address (Street, City, TX ZIP)
        zip_code = f"7{random.randint(5, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
        address = (
            f"{random.randint(100, 9999)} {random.choice(self.STREETS)}, "
            f"{random.choice(self.CITIES)}, TX {zip_code}"
        )

        return Customer(
            customer_name=name,
            customer_email=email,
            customer_company=company,
            customer_address=address
        )

    # -----------------------------
    # SVG LOGO GENERATOR
    # -----------------------------
    def generate_svg_logo(self, company_name: str, color: str) -> str:
        initials = "".join([w[0] for w in company_name.split()[:2]]).upper()
        variant = random.choice(["circle", "square", "text"])

        if variant == "circle":
            return f"""
            <svg width="60" height="60">
                <circle cx="30" cy="30" r="28" fill="{color}" />
                <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"
                      fill="white" font-size="18">{initials}</text>
            </svg>
            """

        elif variant == "square":
            return f"""
            <svg width="60" height="60">
                <rect width="60" height="60" rx="10" fill="{color}" />
                <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"
                      fill="white" font-size="16">{initials}</text>
            </svg>
            """

        else:
            return f"""
            <svg width="160" height="50">
                <text x="0" y="35" font-size="20" fill="{color}" font-weight="bold">
                    {company_name[:15]}
                </text>
            </svg>
            """

    # -----------------------------
    # PDF GENERATION
    # -----------------------------
    def generate_invoice_pdf(self, customer, invoice_num: str, items: list):
        # standard US Date format MM/DD/YYYY
        date = datetime.now().strftime("%m/%d/%Y")

        subtotal = sum(qty * price for _, qty, price in items)
        tax = subtotal * self.TAX_RATE
        total = subtotal + tax

        rows_html = ""
        for name, qty, price in items:
            line_total = qty * price
            rows_html += f"""
            <tr>
                <td>{name}</td>
                <td>{qty}</td>
                <td>${price:,.2f}</td>
                <td>${line_total:,.2f}</td>
            </tr>
            """

        style_variant = random.choice(["classic", "modern"])
        # Deep corporate navy or sophisticated warm amber (appealing to conservative palettes)
        header_color = "#0f172a" if style_variant == "modern" else "#854d0e"

        logo_svg = self.generate_svg_logo(
            customer.customer_company or "Demo Company",
            header_color
        )

        html_content = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            .invoice {{ max-width: 800px; margin:auto; }}
            .header {{ border-bottom: 4px solid {header_color}; margin-bottom: 20px; }}
            h1 {{ color: {header_color}; }}
            table {{ width:100%; border-collapse: collapse; }}
            th, td {{ padding:10px; border-bottom:1px solid #ddd; }}
            th {{ background:#f5f5f5; }}
            .total {{ text-align:right; margin-top:20px; }}
        </style>
        </head>

        <body>
        <div class="invoice">

            <div class="header" style="display:flex; align-items:center; gap:20px;">
                <div>{logo_svg}</div>
                <div>
                    <h1>INVOICE</h1>
                    <p><strong>{customer.customer_company}</strong></p>
                    <p>Invoice #{invoice_num}</p>
                    <p>Date: {date}</p>
                </div>
            </div>

            <p>
            <strong>Bill To:</strong><br>
            {customer.customer_name}<br>
            {customer.customer_email}<br>
            {customer.customer_address}
            </p>

            <table>
                <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Total</th>
                </tr>
                {rows_html}
            </table>

            <div class="total">
                <p>Subtotal: ${subtotal:,.2f}</p>
                <p>Sales Tax (8.25%): ${tax:,.2f}</p>
                <h2>Total: ${total:,.2f}</h2>
            </div>

        </div>
        </body>
        </html>
        """

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        HTML(string=html_content).write_pdf(tmp.name)
        return tmp.name

    # -----------------------------
    # MAIN GENERATOR
    # -----------------------------
    def generate_test_invoices(self, count: int, progress=gr.Progress()):
        if count < 1 or count > 50:
            count = 10

        generated_files = []
        invoice_list = []
        customers = self.service.get_all()

        progress(0.05, desc="Preparing...")

        for i in range(count):
            progress((i + 1) / count, desc=f"Invoice {i+1}/{count}")

            # 🔥 80% NEW, 20% EXISTING
            use_existing = customers and random.random() < 0.2

            if use_existing:
                customer = random.choice(customers)
            else:
                customer = self.generate_random_customer(i)

            items = []
            for _ in range(random.randint(1, 4)):
                name, base_price = random.choice(self.PRODUCTS)
                qty = random.randint(1, 3)
                price = round(base_price * random.uniform(0.9, 1.1), 2)
                items.append((name, qty, price))

            invoice_num = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"

            pdf_path = self.generate_invoice_pdf(customer, invoice_num, items)
            generated_files.append(pdf_path)

            total_amount = sum(q * p for _, q, p in items) * (1 + self.TAX_RATE)

            invoice_list.append({
                "Invoice #": invoice_num,
                "Customer": customer.customer_name,
                "Company": customer.customer_company,
                "Items": len(items),
                "Total ($)": f"{total_amount:,.2f}",
                "File": Path(pdf_path).name
            })

        zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(zip_file.name, 'w') as zipf:
            for pdf in generated_files:
                zipf.write(pdf, arcname=Path(pdf).name)

        return invoice_list, zip_file.name, f"✅ Generated {count} invoices"

    # -----------------------------
    # UI
    # -----------------------------
    def render(self):
        with gr.Column():
            gr.Markdown("# 🧪 Test Invoice Generator")
            gr.Markdown("High-variation synthetic invoices for AI testing.")

            with gr.Row():
                count = gr.Slider(5, 50, value=5, step=5, label="Invoices")
                generate_btn = gr.Button("🚀 Generate", variant="primary")

            status = gr.Textbox(label="Status", interactive=False)

            preview = gr.Dataframe(
                headers=["Invoice #", "Customer", "Company", "Items", "Total ($)", "File"],
                label="Preview"
            )

            download_zip = gr.File(label="Download ZIP", interactive=False)

        generate_btn.click(
            self.generate_test_invoices,
            inputs=count,
            outputs=[preview, download_zip, status]
        )

        return [count, generate_btn, status, preview, download_zip]