# FastAPI Swagger Plugin

This plugin updates the FastAPI app to include a latest Swagger UI distribution. Also, it works locally and does not
depend on the @tiangolo domains and cdns.

## Why?

The FastAPI already includes a Swagger UI. However, author updates swagger not so often. Moreover he uses his own
hosts for the resources, and they are not always available (especially in Russia). This plugin allows to use the latest
Swagger UI distribution and host it inside your app.

## Usage

### Installation

```bash
pip install fastapi-swagger
```

### Basic Usage

```python
from fastapi import FastAPI
from fastapi_swagger import patch_fastapi

app = FastAPI(docs_url=None, swagger_ui_oauth2_redirect_url=None)  # docs url will be at /docs

patch_fastapi(app)
```

## How it works?

How it was before:
FastAPI uses the `get_swagger_ui_html` function to render the Swagger UI under the hood.

```python
def get_swagger_ui_html(
        *,
        openapi_url: str,
        title: str,
        swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
        oauth2_redirect_url: Optional[str] = None,
        init_oauth: Optional[Dict[str, Any]] = None,
        swagger_ui_parameters: Optional[Dict[str, Any]] = None,
) -> HTMLResponse:
    ...
```

How it is now:

Actually, we just copy the Swagger UI distribution from
the [GitHub releases](https://github.com/swagger-api/swagger-ui/releases) to the `fastapi_swagger` package, and serve it
from your app.
Patch creates several additional routes with the Swagger UI resources and one route for docs page (btw, using same
`get_swagger_ui_html` function).

```python
def patch_fastapi(
        app: FastAPI,
        docs_url: str = "/docs",
        *,
        title: Optional[str],
        swagger_js_url: str = "/swagger/swagger-ui-bundle.js",  # relative path from app root
        swagger_css_url: str = "/swagger/swagger-ui.css",  # relative path from app root
        swagger_favicon_url: str = "/swagger/favicon-32x32.png",  # relative path from app root
        oauth2_redirect_url: Optional[str] = None,
        init_oauth: Optional[Dict[str, Any]] = None,
        swagger_ui_parameters: Optional[Dict[str, Any]] = None,
):
    ...


patch_fastapi(app)
# Now there are additional routes /swagger/swagger-ui-bundle.js, /swagger/swagger-ui.css, /swagger/favicon-32x32.png and /docs
# They all are not dependent on the external resources.
```
