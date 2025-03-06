""" Redoc theme functions """

from starlette.responses import HTMLResponse


def get_redoc_html_with_theme(
    *,
    openapi_url: str = "./openapi.json",
    title: str,
    redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    redoc_favicon_url: str = "/favicon.ico",
    with_google_fonts: bool = True,
) -> HTMLResponse:
    """
    Get redoc htm theme

    :param openapi_url: URL for open api
    :param title: The title of the app
    :param redoc_js_url: TODO
    :param redoc_favicon_url: favicon icon locayion
    :param with_google_fonts: option to sue google fonts
    :return:
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>{title}</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """
    if with_google_fonts:
        html += """
    <link href="https://fonts.googleapis.com/css?family=Inter:300,400,700" rel="stylesheet">
    """
    html += (
        f"""
    <link rel="shortcut icon" href="{redoc_favicon_url}">
    <!--
    ReDoc doesn't change outer page styles
    -->
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
    </head>
    <body>
    <div id="redoc-container"></div>
    <noscript>
        ReDoc requires Javascript to function. Please enable it to browse the documentation.
    </noscript>
    <script src="{redoc_js_url}"> </script>
    <script>
        Redoc.init("{openapi_url}", """
        + """{
            "theme": {
                "colors": {
                    "primary": {
                        "main": "#f7ba17",
                        "light": "#ffefc6"
                    },
                    "success": {
                        "main": "rgba(28, 184, 65, 1)",
                        "light": "#81ec9a",
                        "dark": "#083312",
                        "contrastText": "#000"
                    },
                    "text": {
                        "primary": "#14120e",
                        "secondary": "#4d4d4d"
                    },
                    "http": {
                        "get": "#f7ba17",
                        "post": "rgba(28, 184, 65, 1)",
                        "put": "rgba(255, 187, 0, 1)",
                        "delete": "rgba(254, 39, 35, 1)"
                    }
                },
                "typography": {
                    "fontSize": "15px",
                    "fontFamily": "Inter, sans-serif",
                    "lineHeight": "1.5em",
                    "headings": {
                        "fontFamily": "Inter, sans-serif",
                        "fontWeight": "bold",
                        "lineHeight": "1.5em"
                    },
                    "code": {
                        "fontWeight": "600",
                        "color": "rgba(92, 62, 189, 1)",
                        "wrap": true
                    },
                    "links": {
                        "color": "#086788",
                        "visited": "#086788",
                        "hover": "#32343a"
                    }
                },
                "sidebar": {
                    "width": "300px",
                    "textColor": "#000000"
                },
                "logo": {
                    "gutter": "10px"
                },
                "rightPanel": {
                    "backgroundColor": "rgba(55, 53, 71, 1)",
                    "textColor": "#ffffff"
                }
            }
        }"""
        + """, document.getElementById('redoc-container'))
    </script>
    </body>
    </html>
    """
    )
    return HTMLResponse(html)
