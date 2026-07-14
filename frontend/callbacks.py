import json
from urllib.parse import quote_plus

import dash
from dash import Input, Output, State, dcc, html
import requests

from .config import settings

BACKEND_URL = settings.BACKEND_URL


def register_callbacks(app: dash.Dash):
    @app.callback(
        Output("manual-language", "disabled"),
        Input("language-mode", "value"),
    )
    def toggle_manual_language(language_mode):
        return language_mode != "manual"

    @app.callback(
        Output("process-status", "children"),
        Output("progress-bar", "style"),
        Output("progress-bar", "value"),
        Output("status-poll-interval", "disabled"),
        Input("submit-button", "n_clicks"),
        State("file-upload", "contents"),
        State("file-upload", "filename"),
        State("language-mode", "value"),
        State("manual-language", "value"),
    )
    def submit_file(n_clicks, contents, filename, language_mode, manual_language):
        if not n_clicks:
            return "", {"display": "none"}, 0, True
        if not contents or not filename:
            return "Please choose a file first.", {"display": "none"}, 0, True
        import base64
        header, encoded = contents.split(",", 1)
        data = base64.b64decode(encoded)
        response = requests.post(f"{BACKEND_URL}/process", files={"upload_file": (filename, data)}, data={"language_mode": language_mode, "manual_language": manual_language or ""})
        if response.status_code != 200:
            return f"Error: {response.text}", {"display": "none"}, 0, True
        result = response.json()
        if result.get("job_id"):
            return f"Processing long recording: {result['job_id']}", {"display": "block"}, 5, False
        return "Processing complete.", {"display": "none"}, 100, True

    @app.callback(
        Output("transcript-text", "value"),
        Input("cleanup-button", "n_clicks"),
        State("transcript-text", "value"),
        prevent_initial_call=True,
    )
    def update_cleanup(n_clicks, text):
        payload = {"text": text or ""}
        response = requests.post(f"{BACKEND_URL}/enhance/cleanup", json=payload)
        return response.json().get("text", text)

    @app.callback(
        Output("enhancement-output", "children"),
        Input("summarize-button", "n_clicks"),
        Input("action-items-button", "n_clicks"),
        Input("title-button", "n_clicks"),
        State("transcript-text", "value"),
    )
    def handle_enhance(summarize_clicks, action_clicks, title_clicks, text):
        ctx = dash.callback_context
        if not ctx.triggered:
            return ""
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        payload = {"text": text or ""}
        if button_id == "summarize-button":
            response = requests.post(f"{BACKEND_URL}/enhance/summarize", json=payload)
            return response.json().get("summary", "")
        if button_id == "action-items-button":
            response = requests.post(f"{BACKEND_URL}/enhance/action-items", json=payload)
            items = response.json().get("items", [])
            return [html.Ul([html.Li(item) for item in items])]
        if button_id == "title-button":
            response = requests.post(f"{BACKEND_URL}/enhance/title", json=payload)
            return response.json().get("title", "")
        return ""

    @app.callback(
        Output("download-txt", "data"),
        Input("download-button", "n_clicks"),
        State("transcript-text", "value"),
        prevent_initial_call=True,
    )
    def download_transcript(n_clicks, text):
        return dict(content=text or "", filename="transcript.txt")

    @app.callback(
        Output("recording-status", "children"),
        Input("whatsapp-button", "n_clicks"),
        State("transcript-text", "value"),
        prevent_initial_call=True,
    )
    def share_whatsapp(n_clicks, text):
        if not text:
            return "No text to share."
        url = f"https://wa.me/?text={quote_plus(text)}"
        return dcc.Location(href=url, id="whatsapp-link")
