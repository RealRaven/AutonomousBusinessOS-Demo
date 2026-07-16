# presentation/tabs/chat_tab.py
import gradio as gr
from application.chat_service import ChatService


class ChatTab:
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service

    def stream_response(self, message, history):
        if isinstance(message, dict):
            text = message.get("text", "")
            files = message.get("files", [])
        else:
            text = str(message)
            files = []
        yield from self.chat_service.stream_chat(text, files, history)

    def render_floating_chat(self):
        """Toggleable Floating AI Assistant – Final 10/10 version for Gradio 6"""

        with gr.Column(elem_classes=["floating-chat-wrapper"]) as wrapper:
            
            # Glowing Toggle Icon
            toggle_btn = gr.Button(
                "",
                elem_classes=["chat-toggle-btn"],
                size="large",
                variant="primary",
                icon="presentation/assets/img/avatar.png"
            )

            # Full Chat Window (starts hidden)
            with gr.Column(
                elem_classes=["floating-chat-container"], 
                visible=False
            ) as full_chat_container:
                
                with gr.Row(elem_classes=["chat-header-row"]):
                    gr.Markdown("### 🤖 Autonomous Assistant", elem_classes=["chat-header"])
                    close_btn = gr.Button(
                        "✕", 
                        elem_classes=["chat-close-btn"],
                        size="sm",
                        variant="stop"
                    )

                gr.ChatInterface(
                    fn=self.stream_response,
                    multimodal=True,
                    fill_height=True,                    # Allowed here
                    title=None,
                    description=None,
                    textbox=gr.MultimodalTextbox(
                        file_count="multiple",
                        file_types=["image", ".pdf", ".txt"],
                        placeholder="Ask anything or drop files...",
                        show_label=False,
                    ),
                    chatbot=gr.Chatbot(
                        height=440,
                        layout="bubble",
                        avatar_images=[None, "presentation/assets/img/avatar.png"],
                        elem_classes=["chat-message"],
                    ),
                )

        # Toggle Logic
        def show_chat():
            return gr.update(visible=False), gr.update(visible=True)

        def hide_chat():
            return gr.update(visible=True), gr.update(visible=False)

        toggle_btn.click(
            fn=show_chat,
            outputs=[toggle_btn, full_chat_container]
        )

        close_btn.click(
            fn=hide_chat,
            outputs=[toggle_btn, full_chat_container]
        )