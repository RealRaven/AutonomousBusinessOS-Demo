# presentation/ui_manager.py
"""
UI Manager - Orchestrates all tabs and the floating mini chat.
Clean separation between main content and floating assistant.
"""

import gradio as gr
from pathlib import Path

from presentation.tabs.customers_tab import CustomersTab
from presentation.tabs.test_data_tab import TestDataTab
from presentation.tabs.chat_tab import ChatTab


class UIManager:
    def __init__(self, customer_service, chat_service):
        self.customer_service = customer_service
        self.chat_service = chat_service

        # Initialize tabs
        self.customers_tab = CustomersTab(customer_service)
        self.test_data_tab = TestDataTab(customer_service)
        self.chat_tab = ChatTab(chat_service)

    # =============================================================
    # CSS LOADING
    # =============================================================
    def load_css(self) -> str:
        css_path = Path(__file__).parent / "styles.css"

        print(f"[CSS] Looking for: {css_path}")

        if css_path.exists():
            print("[CSS] ✅ Loaded")
            return css_path.read_text(encoding="utf-8")

        print("[CSS] ❌ NOT FOUND")
        return ""
    
    # =============================================================
    # MAIN TABS (Visible in the tab bar)
    # =============================================================
    def render_main_tabs(self):
        with gr.Tab("👥 Customers", id="customers"):
            self.customers_tab.render()

        with gr.Tab("🧪 Test Data", id="test_data"):
            self.test_data_tab.render()

        # Add more tabs here later (Orders, Finance, etc.)

    # =============================================================
    # FLOATING MINI CHAT (Bottom Right Corner)
    # =============================================================
    def render_floating_chat(self):
        """Renders the new toggleable floating AI assistant"""

        self.chat_tab.render_floating_chat()

    # =============================================================
    # Optional: Full interface method (if you want to use it later)
    # =============================================================
    def create_interface(self):
        """Alternative way to build the full Blocks (not used in current run.py)"""
        with gr.Blocks(
            title="Autonomous Business OS Demo",
            fill_height=True,
        ) as demo:
            self.render_main_tabs()
            self.render_floating_chat()
        return demo