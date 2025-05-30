import gradio as gr
from generate_short import generate_short
from upload_to_youtube import upload_to_youtube
from repair_shorts import repair_shorts


def gradio_generate():
    try:
        logs = generate_short()
        return logs
    except Exception as e:
        return f"❌ Error: {str(e)}"


def gradio_upload():
    try:
        logs = upload_to_youtube()
        return logs
    except Exception as e:
        return f"❌ Upload error: {str(e)}"


def gradio_repair():
    try:
        logs = repair_shorts()
        return logs
    except Exception as e:
        return f"❌ Repair error: {str(e)}"


with gr.Blocks() as demo:
    gr.Markdown("## 🎬 Jay & Tiger Shorts Automation Console")
    log_output = gr.Textbox(label="Logs", lines=20)

    with gr.Row():
        gen_btn = gr.Button("Generate Short")
        upload_btn = gr.Button("Upload to YouTube")
        repair_btn = gr.Button("Repair Shorts")

    gen_btn.click(fn=gradio_generate, outputs=log_output)
    upload_btn.click(fn=gradio_upload, outputs=log_output)
    repair_btn.click(fn=gradio_repair, outputs=log_output)


demo.launch()
