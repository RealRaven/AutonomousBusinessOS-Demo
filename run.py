# run.py
"""
Main entry point for Autonomous Business OS
"""

import gradio as gr
import ollama
from rich.console import Console

from config.settings import settings
from infrastructure.llm.ollama_client import OllamaClient
from infrastructure.database.chroma_client import ChromaClient
from application.customer_service import CustomerService
from application.chat_service import ChatService
from presentation.ui_manager import UIManager

console = Console()

def main():
    console.print("[bold cyan]Launching Autonomous Business OS Demo[/bold cyan]")
    console.print("[dim] Cinematic UI with floating AI assistant[/dim]\n")

    # Infrastructure
    try:
        ollama.list()
        console.print("[green]✓ Ollama is reachable[/green]")
    except Exception as e:
        console.print(f"[red]✗ Ollama not reachable: {e}[/red]")

    ollama_client = OllamaClient()
    chroma_client = ChromaClient()

    customer_service = CustomerService(chroma_client=chroma_client, ollama_client=ollama_client)
    chat_service = ChatService(ollama_client=ollama_client)

    ui_manager = UIManager(customer_service=customer_service, chat_service=chat_service)

    # =========================================================
    # OPTIMIZED STARFIELD — GPU friendly
    # =========================================================
    js_canvas = """
    function initStars() {
        if (window.__starsInit) return;
        window.__starsInit = true;
        
        const canvas = document.getElementById("space-canvas");
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d", { alpha: true });
        let w = canvas.width = window.innerWidth;
        let h = canvas.height = window.innerHeight;
        
        // --- Config: fewer stars, slower, smaller ---
        const STAR_COUNT = 25;
        const TARGET_FPS = 24;
        const FRAME_MIN = 1000 / TARGET_FPS;
        
        const stars = [];
        for (let i = 0; i < STAR_COUNT; i++) {
            stars.push({
                x: Math.random() * w,
                y: Math.random() * h,
                r: Math.random() * 1.0 + 0.3,   // smaller radius
                s: Math.random() * 0.12 + 0.03  // slower speed
            });
        }
        
        let lastTime = 0;
        let rafId = null;
        
        function draw(timestamp) {
            rafId = requestAnimationFrame(draw);
            
            // Throttle to ~24 FPS + pause when tab hidden
            if (document.hidden) return;
            if (timestamp - lastTime < FRAME_MIN) return;
            lastTime = timestamp;
            
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = "rgba(255, 255, 255, 0.75)";
            
            // Batch all stars into a single path
            ctx.beginPath();
            for (let s of stars) {
                ctx.moveTo(s.x + s.r, s.y);
                ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
                
                s.y += s.s;
                if (s.y > h) {
                    s.y = -2;
                    s.x = Math.random() * w;
                }
            }
            ctx.fill();
        }
        
        window.addEventListener("resize", () => {
            w = canvas.width = window.innerWidth;
            h = canvas.height = window.innerHeight;
        });
        
        // Cleanup on page hide (save battery/GPU)
        document.addEventListener("visibilitychange", () => {
            if (document.hidden && rafId) {
                cancelAnimationFrame(rafId);
                rafId = null;
            } else if (!document.hidden && !rafId) {
                rafId = requestAnimationFrame(draw);
            }
        });
        
        rafId = requestAnimationFrame(draw);
    }
    """

    with gr.Blocks(
        title=settings.app_title,
        fill_height=True,
    ) as app:

        # FULL-SCREEN BACKGROUND CANVAS
        gr.HTML(
            '''<canvas id="space-canvas" 
                style="position: fixed; 
                       top: 0; 
                       left: 0; 
                       width: 100vw; 
                       height: 100vh; 
                       z-index: -1; 
                       pointer-events: none;">
            </canvas>'''
        )

        # Main content
        with gr.Column(elem_classes="main-content"):
            with gr.Row():
                gr.Markdown(f"# {settings.app_title}")
                gr.Markdown("### AI-Powered Business Management with RAG")

            with gr.Row():
                gr.Markdown("**Status:** `Online` • Local • Ollama + Chroma")

            with gr.Tabs():
                ui_manager.render_main_tabs()

        # Floating Mini Chat
        ui_manager.render_floating_chat()

        app.load(None, None, None, js="initStars()")

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        share=False,
        debug=False,
        theme=gr.themes.Monochrome(),
        css=ui_manager.load_css(),
        js=js_canvas,
    )


if __name__ == "__main__":
    main()