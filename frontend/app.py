from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from callbacks import register_callbacks

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(html.H1("VoiceScribe AI", className="app-title"), width=12),
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Quick Capture & Meeting Mode", className="card-title"),
                            dcc.RadioItems(
                                id="mode-selector",
                                options=[
                                    {"label": "Quick Capture", "value": "quick"},
                                    {"label": "Meeting Mode", "value": "meeting"},
                                ],
                                value="quick",
                                inline=True,
                            ),
                            html.Hr(),
                            dbc.Button("Record Audio", id="record-button", color="primary", className="me-2"),
                            html.Button("Download Transcript", id="download-button", className="btn btn-secondary"),
                            dcc.Download(id="download-txt"),
                            html.Div(id="recording-status", className="mt-2 text-muted"),
                        ]
                    ),
                    className="mb-4",
                ),
            ),
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Upload / Record Input", className="card-title"),
                            dcc.Upload(
                                id="file-upload",
                                children=html.Div(["Drag and drop or click to select an audio/video file"]),
                                className="upload-box",
                                multiple=False,
                            ),
                            html.Div(id="upload-output", className="mt-2"),
                            html.Hr(),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Language Mode"),
                                            dcc.RadioItems(
                                                id="language-mode",
                                                options=[
                                                    {"label": "Automatic", "value": "automatic"},
                                                    {"label": "Manual", "value": "manual"},
                                                ],
                                                value="automatic",
                                                inline=True,
                                            ),
                                        ]
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Manual Language"),
                                            dcc.Dropdown(
                                                id="manual-language",
                                                options=[
                                                    {"label": lang, "value": lang}
                                                    for lang in ["en", "es", "fr", "de", "hi", "zh", "ja"]
                                                ],
                                                disabled=True,
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            dbc.Button("Submit", id="submit-button", color="warning", className="mt-3"),
                            dbc.Progress(
                                id="progress-bar",
                                value=0,
                                striped=True,
                                animated=True,
                                className="mt-3",
                                style={"display": "none"},
                            ),
                            html.Div(id="process-status", className="mt-2"),
                            dcc.Interval(id="status-poll-interval", interval=3000, disabled=True),
                        ]
                    ),
                    className="mb-4",
                ),
            ),
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Transcript", className="card-title"),
                            dcc.Textarea(id="transcript-text", style={"width": "100%", "height": "240px"}),
                            dbc.Button("Share to WhatsApp", id="whatsapp-button", color="success", className="mt-2 me-2"),
                        ]
                    ),
                    className="mb-4",
                ),
            ),
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5("Enhancements"),
                                dbc.Button("Clean Up", id="cleanup-button", color="secondary", className="me-2"),
                                dbc.Button("Summarize", id="summarize-button", color="secondary", className="me-2"),
                                dbc.Button("Action Items", id="action-items-button", color="secondary", className="me-2"),
                                dbc.Button("Auto Title", id="title-button", color="secondary", className="me-2"),
                                html.Div(id="enhancement-output", className="mt-3"),
                            ]
                        )
                    ),
                    width=12,
                )
            ]
        ),
    ],
    fluid=True,
    className="app-container",
)

register_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)