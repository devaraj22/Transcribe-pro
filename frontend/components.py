from dash import dcc, html
import dash_bootstrap_components as dbc


def upload_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Upload / Record Input", className="card-title"),
            dcc.Upload(id="file-upload", className="upload-box", children=html.Div(["Drag and drop or click to select an audio/video file"])),
        ]),
    ])
