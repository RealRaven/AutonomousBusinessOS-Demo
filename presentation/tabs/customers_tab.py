# presentation/tabs/customers_tab.py
"""
Customers Tab - Checkbox table selection + explicit Edit button.
No auto-save on typing.
"""

import gradio as gr
import tempfile
import zipfile
import os
from pathlib import Path

from config.settings import settings
from core.models import Customer
from application.customer_service import CustomerService


class CustomersTab:
    def __init__(self, customer_service: CustomerService):
        self.service = customer_service
        self.components = {}

    def get_title(self):
        return "👥 Customers"

    def _to_rows(self, df_data):
        """Normalize Gradio DataFrame output to list of lists."""
        if df_data is None:
            return []
        if hasattr(df_data, 'values'):
            return df_data.values.tolist()
        if hasattr(df_data, 'tolist'):
            return df_data.tolist()
        return list(df_data)

    def _find_checked_id(self, df_data):
        """Return the ID of the first row whose checkbox is True."""
        rows = self._to_rows(df_data)
        for row in rows:
            if len(row) > 1 and row[0] is True:
                return row[1]
        return None

    def _refresh_table(self, keep_selected: str = None):
        """Build table data with checkbox column."""
        df = self.service.to_dataframe()
        return [[row[0] == keep_selected] + row for row in df]

    # =============================================================
    # BULK UPLOAD
    # =============================================================
    def process_bulk_upload(self, files, progress=gr.Progress()):
        if not files:
            return "❌ No files uploaded.", [], "Upload something first.", self._refresh_table()

        import concurrent.futures

        results = []
        errors = []
        saved_count = 0
        all_paths = []

        for f in files:
            path = f.name if hasattr(f, "name") else str(f)
            if not os.path.exists(path):
                continue

            if path.lower().endswith('.zip'):
                try:
                    tmpdir = tempfile.mkdtemp()
                    with zipfile.ZipFile(path, 'r') as zip_ref:
                        zip_ref.extractall(tmpdir)
                    for root, _, filenames in os.walk(tmpdir):
                        for fname in filenames:
                            all_paths.append(os.path.join(root, fname))
                except Exception as e:
                    errors.append(f"ZIP extraction failed: {str(e)}")
            else:
                all_paths.append(path)

        total = len(all_paths)

        def worker(file_path):
            try:
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                    data = self.service.ollama_client.extract_from_image(file_path)
                elif file_path.lower().endswith('.pdf'):
                    data = self.service.ollama_client.extract_from_pdf(file_path)
                else:
                    prompt = """Extract customer data. Return ONLY JSON:
{
"customer_name": "",
"customer_email": "",
"customer_phone": "",
"customer_company": "",
"customer_address": "",
"customer_notes": ""
}
"""
                    raw = self.service.ollama_client.call_generate(prompt)
                    data = self.service.ollama_client.safe_json_parse(raw)

                if hasattr(data, 'model_dump'):
                    data = data.model_dump()

                if not data or (not data.get("customer_name") and not data.get("customer_email")):
                    return ("skip", f"Skipped: {Path(file_path).name}")

                customer = Customer(
                    customer_name=data.get("customer_name", "").strip(),
                    customer_email=data.get("customer_email", "").strip(),
                    customer_phone=data.get("customer_phone", "").strip(),
                    customer_company=data.get("customer_company", "").strip(),
                    customer_address=data.get("customer_address", "").strip(),
                    customer_notes=f"Auto-extracted from {Path(file_path).name}",
                )

                if customer.customer_email:
                    existing = self.service.search(customer.customer_email)
                    if any(e.customer_email and e.customer_email.lower() == customer.customer_email.lower()
                           for e in existing):
                        return ("dup", f"⏭️ Duplicate: {customer.customer_email}")

                new_id = self.service.add_customer(customer)
                return ("ok", f"✅ {new_id}: {customer.customer_name}")

            except Exception as e:
                return ("err", f"{Path(file_path).name}: {str(e)}")

        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, p) for p in all_paths]
            for future in concurrent.futures.as_completed(futures):
                status, msg = future.result()
                completed += 1
                progress(completed / total, desc=f"{completed}/{total} processed")
                if status == "ok":
                    results.append(msg)
                    saved_count += 1
                elif status in ("dup", "skip"):
                    results.append(msg)
                else:
                    errors.append(msg)

        total_in_db = len(self.service.get_all())
        summary = (
            f"🎉 Bulk import completed!\n"
            f"Files processed: {total}\n"
            f"Customers saved: {saved_count}\n"
            f"📦 Total in database: {total_in_db}"
        )
        return summary, results, "\n".join(errors) if errors else "No errors", self._refresh_table()

    # =============================================================
    # AI FILL
    # =============================================================
    def ai_fill_from_text(self, description: str):
        if not description.strip():
            return [gr.update(value="")] * 6

        prompt = f"""Extract customer information from this description:
{description}

Return only valid JSON with these fields:
{{"customer_name": "", "customer_email": "", "customer_phone": "", 
  "customer_company": "", "customer_address": "", "customer_notes": ""}}"""

        raw = self.service.ollama_client.call_generate(prompt)
        return self._parse_output(raw)

    def ai_fill_from_image(self, file):
        if file is None:
            return [gr.update(value="")] * 6

        file_path = file.name if hasattr(file, "name") else str(file)

        try:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                data = self.service.ollama_client.extract_from_image(file_path)
            elif file_path.lower().endswith('.pdf'):
                data = self.service.ollama_client.extract_from_pdf(file_path)
            else:
                prompt = """Extract customer information.
Return only valid JSON with:
customer_name, customer_email, customer_phone,
customer_company, customer_address, customer_notes."""
                raw = self.service.ollama_client.call_generate(f"{prompt}\n\nFile: {file_path}")
                return self._parse_output(raw)

            return self._parse_output(data)

        except Exception as e:
            print("AI scan error:", e)
            return [gr.update(value="")] * 6

    def _parse_output(self, raw):
        if hasattr(raw, 'model_dump'):
            data = raw.model_dump()
        elif isinstance(raw, dict):
            data = raw
        else:
            data = self.service.ollama_client.safe_json_parse(str(raw))

        return [
            gr.update(value=data.get("customer_name", "")),
            gr.update(value=data.get("customer_email", "")),
            gr.update(value=data.get("customer_phone", "")),
            gr.update(value=data.get("customer_company", "")),
            gr.update(value=data.get("customer_address", "")),
            gr.update(value=data.get("customer_notes", "")),
        ]

    # =============================================================
    # MANUAL CRUD
    # =============================================================
    def save_customer(self, name, email, phone, company, address, notes, selected_id=None):
        if not name or not email:
            return "⚠️ Name and Email are required!", self._refresh_table()

        customer = Customer(
            customer_id=selected_id if selected_id and selected_id != "AUTO-GEN" else "",
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            customer_company=company,
            customer_address=address,
            customer_notes=notes
        )

        if selected_id and selected_id != "AUTO-GEN":
            # Remove customer_id from kwargs so we don't pass it twice
            data = customer.to_dict()
            data.pop("customer_id", None)
            success = self.service.update_customer(selected_id, **data)
            msg = f"✅ Updated {selected_id}" if success else "❌ Customer not found"
        else:
            existing = self.service.search(email)
            if any(e.customer_email and e.customer_email.lower() == email.lower() for e in existing):
                return f"⚠️ Email '{email}' already exists!", self._refresh_table()

            new_id = self.service.add_customer(customer)
            msg = f"✅ Created {new_id}"

        return msg, self._refresh_table()

    def clear_form(self):
        """🧹 Reset all form fields to empty."""
        return [
            gr.update(value="AUTO-GEN"),   # customer_id
            gr.update(value=""),           # customer_name
            gr.update(value=""),           # customer_email
            gr.update(value=""),           # customer_phone
            gr.update(value=""),           # customer_company
            gr.update(value=""),           # customer_address
            gr.update(value=""),           # customer_notes
            gr.update(value="🧹 Form cleared")  # output_msg
        ]

    def load_selected(self, df_data):
        """✏️ Load the checked row into the form."""
        selected_id = self._find_checked_id(df_data)
        if not selected_id:
            return [gr.update()] * 7

        customer = self.service.get_customer(selected_id)
        if not customer:
            return [gr.update()] * 7

        return [
            gr.update(value=customer.customer_id),
            gr.update(value=customer.customer_name),
            gr.update(value=customer.customer_email),
            gr.update(value=customer.customer_phone),
            gr.update(value=customer.customer_company),
            gr.update(value=customer.customer_address),
            gr.update(value=customer.customer_notes),
        ]

    def delete_selected(self, df_data):
        """🗑️ Delete the row whose checkbox is ticked."""
        selected_id = self._find_checked_id(df_data)
        if not selected_id:
            return (
                "⚠️ Check a box in the table first",
                self._refresh_table(),
                gr.update(value="AUTO-GEN"),
                *[gr.update(value="")] * 6
            )

        success = self.service.delete_customer(selected_id)
        msg = f"🗑️ Deleted {selected_id}" if success else "❌ Not found"
        return (
            msg,
            self._refresh_table(),
            gr.update(value="AUTO-GEN"),
            *[gr.update(value="")] * 6
        )

    # =============================================================
    # RAG QUERY
    # =============================================================
    def ask_llm_with_rag(self, query: str) -> str:
        if not query.strip():
            return "Please enter a question."

        result = self.service.rag_search(query, n_results=5)
        answer = result.get("answer", "No answer generated.")
        context = result.get('context', "No data available.")

        return f"🤖 **Answer:**\n{answer}\n\n---\n📚 **Context Used:**\n{context}"

    # =============================================================
    # RENDER UI
    # =============================================================
    def render(self):
        with gr.Row():
            # Left Column
            with gr.Column(scale=1, min_width=420):
                gr.Markdown("### 📦 Bulk Import from Invoices / Images / PDFs")
                self.components['bulk_files'] = gr.File(
                    label="Drop files, PDFs or ZIP here",
                    file_count="multiple",
                    file_types=["image", ".zip", ".pdf"],
                    height=160
                )
                bulk_btn = gr.Button("🚀 Process & Auto-Save All Customers", variant="primary", size="large")

                self.components['bulk_status'] = gr.Textbox(label="Processing Status", interactive=False, lines=3)
                self.components['bulk_results'] = gr.JSON(label="Extraction Results")
                self.components['bulk_errors'] = gr.Textbox(label="Errors / Skipped Items", interactive=False, lines=4)

                gr.Markdown("---")
                gr.Markdown("#### 🤖 Single Entry AI Fill")

                self.components['ai_description'] = gr.TextArea(lines=2, placeholder="Describe the customer...")
                ai_text_btn = gr.Button("✍️ Fill from Text", size="sm")

                self.components['ai_file'] = gr.File(file_types=["image", ".pdf"], label="Upload, scan, or drop a PDF")
                ai_image_btn = gr.Button("📸 Scan", size="sm")

                gr.Markdown("---")
                gr.Markdown("### 📝 Manual Customer Form")

                with gr.Group():
                    self.components['customer_id'] = gr.Textbox(label="Customer ID", interactive=False, value="AUTO-GEN")
                    self.components['customer_name'] = gr.Textbox(label="Full Name *")
                    self.components['customer_email'] = gr.Textbox(label="Email *")
                    self.components['customer_phone'] = gr.Textbox(label="Phone")
                    self.components['customer_company'] = gr.Textbox(label="Company")
                    self.components['customer_address'] = gr.TextArea(label="Address", lines=2)
                    self.components['customer_notes'] = gr.TextArea(label="Notes", lines=2)

                # Save + Clear buttons side by side
                with gr.Row():
                    save_btn = gr.Button("💾 Save Customer", variant="primary", scale=2)
                    clear_btn = gr.Button("🧹 Clear Form", variant="secondary", scale=1)

                self.components['output_msg'] = gr.Textbox(label="Status", interactive=False)

            # Right Column
            with gr.Column(scale=2):
                gr.Markdown("### 🗄️ Customer Database")

                self.components['rag_query'] = gr.Textbox(
                    label="Ask about your customers (RAG)",
                    placeholder="e.g. Show me all customers from TechNova",
                    lines=2
                )
                rag_ask_btn = gr.Button("🤖 Ask LLM with RAG", variant="primary")
                self.components['rag_output'] = gr.Markdown("Results will appear here...")

                # Table with checkbox column (interactive so boxes are clickable)
                self.components['customers_table'] = gr.Dataframe(
                    headers=["Select", "ID", "Name", "Email", "Phone", "Company", "Address", "Notes"],
                    value=self._refresh_table(),
                    datatype=["bool"] + ["str"] * 7,
                    max_height=420,
                    interactive=True,
                    elem_classes=["glass-card"]
                )

                # Action buttons for the table
                with gr.Row():
                    edit_btn = gr.Button("✏️ Edit Selected", variant="secondary", size="sm")
                    delete_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm")

                gr.Markdown(f"Powered by ChromaDB + {settings.embedding_model}")

        # ====================== Event Bindings ======================

        bulk_btn.click(
            self.process_bulk_upload,
            inputs=self.components['bulk_files'],
            outputs=[
                self.components['bulk_status'],
                self.components['bulk_results'],
                self.components['bulk_errors'],
                self.components['customers_table']
            ]
        )

        ai_text_btn.click(
            self.ai_fill_from_text,
            inputs=self.components['ai_description'],
            outputs=[self.components[c] for c in [
                'customer_name', 'customer_email', 'customer_phone',
                'customer_company', 'customer_address', 'customer_notes'
            ]]
        )

        ai_image_btn.click(
            self.ai_fill_from_image,
            inputs=self.components['ai_file'],
            outputs=[self.components[c] for c in [
                'customer_name', 'customer_email', 'customer_phone',
                'customer_company', 'customer_address', 'customer_notes'
            ]]
        )

        save_btn.click(
            self.save_customer,
            inputs=[self.components[c] for c in [
                'customer_name', 'customer_email', 'customer_phone',
                'customer_company', 'customer_address', 'customer_notes', 'customer_id'
            ]],
            outputs=[self.components['output_msg'], self.components['customers_table']]
        )

        # 🧹 Clear Form button
        clear_btn.click(
            self.clear_form,
            outputs=[self.components[c] for c in [
                'customer_id', 'customer_name', 'customer_email',
                'customer_phone', 'customer_company', 'customer_address', 'customer_notes', 'output_msg'
            ]]
        )

        # ✏️ Edit Selected: reads checkbox, loads into form
        edit_btn.click(
            self.load_selected,
            inputs=self.components['customers_table'],
            outputs=[self.components[c] for c in [
                'customer_id', 'customer_name', 'customer_email',
                'customer_phone', 'customer_company', 'customer_address', 'customer_notes'
            ]]
        )

        # 🗑️ Delete Selected: reads checkbox, deletes row
        delete_btn.click(
            self.delete_selected,
            inputs=self.components['customers_table'],
            outputs=[
                self.components['output_msg'],
                self.components['customers_table'],
                self.components['customer_id']
            ] + [self.components[c] for c in [
                'customer_name', 'customer_email', 'customer_phone',
                'customer_company', 'customer_address', 'customer_notes'
            ]]
        )

        rag_ask_btn.click(
            self.ask_llm_with_rag,
            inputs=self.components['rag_query'],
            outputs=self.components['rag_output']
        )

        return list(self.components.values())