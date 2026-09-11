import gradio as gr
from dotenv import load_dotenv
from research_manager import ResearchManager
from styles import CSS, JS, EXAMPLES, HEADER_HTML, wait_markup

load_dotenv(override=True)


def prepare(
    query: str,
    awaiting: bool,
    audience: str,
    scope: str,
    success: str,
    button_label: str,
):
    query = (query or "").strip()

    if not query:
        return (
            gr.update(visible=False),
            False,
            gr.update(value="Investigate", interactive=True),
            "",
            "",
            "",
            gr.update(),
            gr.update(value="", visible=False),
            "Enter a research question first.",
            None,
        )

    ready_to_run = awaiting or (button_label or "").strip().lower() == "continue"
    if not ready_to_run:
        return (
            gr.update(visible=True),
            True,
            gr.update(value="Continue", interactive=True),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(value="", visible=False),
            "Answer the 3 questions below, then click Continue.",
            None,
        )

    job = {
        "query": query,
        "clarifications": {
            "audience": (audience or "").strip(),
            "scope": (scope or "").strip(),
            "success": (success or "").strip(),
        },
    }
    return (
        gr.update(visible=False),
        False,
        gr.update(value="Investigate", interactive=False),
        "",
        "",
        "",
        gr.update(value="", interactive=False),
        gr.update(value=wait_markup("Starting research..."), visible=True),
        "",
        job,
    )


async def run_research(job: dict | None):
    skip = (gr.skip(), gr.skip(), gr.skip(), gr.skip())
    if not job:
        yield skip
        return

    try:
        pending = None
        async for update in ResearchManager().run(job["query"], job["clarifications"]):
            if pending is not None:
                yield (
                    gr.update(value=wait_markup(pending), visible=True),
                    gr.skip(),
                    gr.skip(),
                    gr.skip(),
                )
            pending = update
        yield (
            gr.update(value="", visible=False),
            pending or "",
            gr.update(interactive=True),
            gr.update(interactive=True),
        )
    except Exception as exc:
        yield (
            gr.update(value="", visible=False),
            f"Research failed: {exc}",
            gr.update(interactive=True),
            gr.update(interactive=True),
        )


with gr.Blocks(title="Deep Research") as ui:
    gr.HTML(HEADER_HTML)

    with gr.Row(elem_classes="dr-query-row"):
        query_textbox = gr.Textbox(
            placeholder="Type a research question...",
            show_label=False,
            container=False,
            autofocus=True,
            elem_id="dr-query",
            scale=5,
        )
        run_button = gr.Button("Investigate", variant="primary", elem_id="dr-run", scale=1)

    with gr.Column(visible=False, elem_id="dr-clarify") as clarify_box:
        gr.HTML('<div class="dr-examples-label">Clarify</div>')
        audience = gr.Textbox(
            label="Audience and purpose",
            placeholder="Who is this for, and what should they do with the answer?",
            lines=2,
            elem_id="dr-audience",
        )
        scope = gr.Textbox(
            label="Scope and constraints",
            placeholder="Time range, geography, industry, or sources to include or exclude",
            lines=2,
            elem_id="dr-scope",
        )
        success = gr.Textbox(
            label="Success criteria",
            placeholder="Length, must-cover topics, format, or a claim to verify",
            lines=2,
            elem_id="dr-success",
        )

    awaiting_answers = gr.State(False)
    research_job = gr.State(None)

    gr.HTML('<div class="dr-examples-label">Try one</div>')
    gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples")

    wait_panel = gr.HTML(visible=False, elem_id="dr-wait-panel")
    report = gr.Markdown(elem_id="dr-report")

    prepare_inputs = [query_textbox, awaiting_answers, audience, scope, success, run_button]
    prepare_outputs = [
        clarify_box,
        awaiting_answers,
        run_button,
        audience,
        scope,
        success,
        query_textbox,
        wait_panel,
        report,
        research_job,
    ]
    research_outputs = [wait_panel, report, query_textbox, run_button]

    def bind(event):
        event(prepare, inputs=prepare_inputs, outputs=prepare_outputs).then(
            run_research, inputs=research_job, outputs=research_outputs
        )

    bind(run_button.click)
    bind(query_textbox.submit)
    bind(audience.submit)
    bind(scope.submit)
    bind(success.submit)


if __name__ == "__main__":
    ui.launch(css=CSS, js=JS, theme=gr.themes.Base())
