import warnings
from importlib import resources
from typing import Optional, Dict, Any

from fastapi import FastAPI, Response, Request
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import RedirectResponse


def patch_fastapi(
    app: FastAPI,
    docs_url: str = "/docs",
    redirect_from_root_to_docs: bool = True,
    *,
    title: Optional[str] = None,
    swagger_js_url: str = "/swagger/swagger-ui-bundle.js",  # relative path from app root
    swagger_css_url: str = "/swagger/swagger-ui.css",  # relative path from app root
    swagger_favicon_url: str = "/swagger/favicon-32x32.png",  # relative path from app root
    oauth2_redirect_url: Optional[str] = None,
    init_oauth: Optional[Dict[str, Any]] = None,
    swagger_ui_parameters: Optional[Dict[str, Any]] = None,
):
    """
    Patch FastAPI app to serve Swagger UI using fastapi_swagger plugin

    :param app: FastAPI app
    :param docs_url: URL to serve Swagger UI
    :param redirect_from_root_to_docs: Redirect from root to Swagger UI (default: True)
    :param title: Title of Swagger UI page (default: f"{app.title} - Swagger UI") - html title
    :param swagger_js_url: Where to serve Swagger UI JS bundle
    :param swagger_css_url: Where to serve Swagger UI CSS
    :param swagger_favicon_url: Where to serve Swagger UI favicon image - html icon
    :param swagger_ui_parameters: Parameters for Swagger UI
     (default: {"tryItOutEnabled": True, "persistAuthorization": True, "filter": True})
    :param init_oauth: OAuth2 configuration
    :param oauth2_redirect_url: OAuth2 redirect URL
    """
    # docs_url=None, swagger_ui_oauth2_redirect_url=None should be set in FastAPI app definition
    if getattr(app, "docs_url", None) is not None:
        warnings.warn(
            "`docs_url` is set in FastAPI app definition, please, set it to None",
            UserWarning,
        )
    if getattr(app, "swagger_ui_oauth2_redirect_url", None) is not None:
        warnings.warn(
            "`swagger_ui_oauth2_redirect_url` is set in FastAPI app definition, please, set it to None",
            UserWarning,
        )

    if redirect_from_root_to_docs:

        @app.get("/", include_in_schema=False)
        async def redirect_to_docs(request: Request):
            return RedirectResponse(url=request.url_for("swagger_ui_html"))

    @app.get(docs_url, tags=["Swagger"], include_in_schema=False)
    async def swagger_ui_html(request: Request):
        nonlocal swagger_ui_parameters, title, oauth2_redirect_url
        root_path = request.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + app.openapi_url
        _swagger_js_url = request.url_for("swagger_ui_bundle_js")
        _swagger_css_url = request.url_for("swagger_ui_css")
        _swagger_favicon_url = request.url_for("swagger_favicon_png")
        if swagger_ui_parameters is None:
            swagger_ui_parameters = {
                "tryItOutEnabled": True,
                "persistAuthorization": True,
                "filter": True,
            }
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=title or f"{app.title} - Swagger UI",
            swagger_js_url=str(_swagger_js_url),
            swagger_css_url=str(_swagger_css_url),
            swagger_favicon_url=str(_swagger_favicon_url),
            oauth2_redirect_url=oauth2_redirect_url,
            init_oauth=init_oauth,
            swagger_ui_parameters=swagger_ui_parameters,
        )

    @app.get(swagger_js_url, tags=["Swagger"], include_in_schema=False)
    async def swagger_ui_bundle_js() -> Response:
        with resources.open_binary(
            "fastapi_swagger.resources", "swagger-ui-bundle.js"
        ) as f:
            _ = f.read()
            return Response(content=_, media_type="application/javascript")

    @app.get(swagger_css_url, tags=["Swagger"], include_in_schema=False)
    async def swagger_ui_css() -> Response:
        with resources.open_binary("fastapi_swagger.resources", "swagger-ui.css") as f:
            _ = f.read()
            return Response(content=_, media_type="text/css")

    @app.get(swagger_favicon_url, tags=["Swagger"], include_in_schema=False)
    async def swagger_favicon_png() -> Response:
        with resources.open_binary(
            "fastapi_swagger.resources", "favicon-32x32.png"
        ) as f:
            _ = f.read()
            return Response(content=_, media_type="image/png")
