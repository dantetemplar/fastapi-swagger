import json
import warnings
from importlib import resources
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from starlette.responses import HTMLResponse, RedirectResponse
from typing_extensions import Annotated, Doc

swagger_ui_default_parameters: Annotated[
    Dict[str, Any],
    Doc(
        """
        Default configurations for Swagger UI.

        You can use it as a template to add any other configurations needed.
        """
    ),
] = {
    "dom_id": "#swagger-ui",
    "layout": "BaseLayout",
    "deepLinking": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "tryItOutEnabled": True,
    "persistAuthorization": True,
    "filter": True,
    "displayRequestDuration": True,
    "requestSnippetsEnabled": True,
    "requestSnippets": {
        "generators": {
            "tanstack": {
                "title": "TanStack",
                "syntax": "javascript",
            },
        },
        "languages": ["curl_bash", "tanstack"],
    },
}


js_patch = r"""
const SnippedGeneratorNodeJsPlugin = {
  fn: {
    /**
     * Helper: Convert Immutable.Map to plain JS object
     */
    mapToObject: (map) => {
      const result = {};
      if (map instanceof Map) {
        map.forEach((val, key) => {
          result[key] = val;
        });
      }
      return result;
    },

    /**
     * Main TanStack + $api snippet generator (supports query/body/path params)
     */
    requestSnippetGenerator_tanstack: (request) => {
      const url = new URL(request.get("url"));
      const method = request.get("method")?.toUpperCase() || "GET";
      const headers = request.get("headers");
      let isMultipartFormDataRequest = false;

      // Detect multipart/form-data
      if (headers && headers.size) {
        headers.map((val, key) => {
          if (
            /^content-type$/i.test(key) &&
            /^multipart\/form-data$/i.test(val)
          ) {
            isMultipartFormDataRequest = true;
          }
        });
      }

      console.log([...request.entries()]);
      // Extract query params from URL
      const queryParams = {};
      for (const [key, val] of url.searchParams.entries()) {
        queryParams[key] = val;
      }

      // Extract body
      let rawBody = request.get("body");
      let bodyParams = undefined;

      if (rawBody) {
        if (
          isMultipartFormDataRequest &&
          ["POST", "PUT", "PATCH"].includes(method)
        ) {
          return `throw new Error("Currently unsupported content-type: /^multipart\\/form-data$/i");`;
        }

        if (rawBody instanceof Map) {
          bodyParams = SnippedGeneratorNodeJsPlugin.fn.mapToObject(rawBody);
        } else if (typeof rawBody === "string") {
          try {
            bodyParams = JSON.parse(rawBody);
          } catch (err) {
            bodyParams = rawBody; // fallback: send raw string
          }
        } else if (typeof rawBody === "object") {
          bodyParams = rawBody;
        }
      }

      // Compose final config object passed to $api
      const configObject = {};
      if (Object.keys(queryParams).length > 0) {
        configObject.query = queryParams;
      }
      if (bodyParams !== undefined) {
        configObject.body = bodyParams;
      }

      // Format config object (if any)
      const configString = Object.keys(configObject).length > 0
        ? `,\n  ${JSON.stringify(configObject, null, 2)}`
        : "";

      const serviceName = "TANSTACK_API_CLIENT";
      const importPath = `@/api${serviceName !== "api" ? `/${serviceName}` : ""}`;

      let code = `import { $${serviceName}, ${serviceName}Types } from "${importPath}";\n\n`;

      const endpoint = url.pathname;

      if (method === "GET") {
        code += `const { data, isPending, error, refetch } = $${serviceName}.useQuery(\n` +
                `  "${method}",\n` +
                `  "${endpoint}"${configString}\n` +
                `);\n\n` +
                `console.log(data, isPending, error);\n`;
      } else {
        code += `const mutation = $${serviceName}.useMutation(\n` +
                `  "${method}",\n` +
                `  "${endpoint}"${configString}\n` +
                `);\n\n` +
                `mutation.mutate();\n\n` +
                `console.log(mutation.data, mutation.isPending, mutation.error);\n`;
      }

      return code;
    }
  }
};
"""


def get_swagger_ui_html(
    *,
    openapi_url: Annotated[
        str,
        Doc(
            """
            The OpenAPI URL that Swagger UI should load and use.

            This is normally done automatically by FastAPI using the default URL
            `/openapi.json`.
            """
        ),
    ],
    title: Annotated[
        str,
        Doc(
            """
            The HTML `<title>` content, normally shown in the browser tab.
            """
        ),
    ],
    tanstack_api_client: str | None = None,
    swagger_js_url: Annotated[
        str,
        Doc(
            """
            The URL to use to load the Swagger UI JavaScript.

            It is normally set to a CDN URL.
            """
        ),
    ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    swagger_css_url: Annotated[
        str,
        Doc(
            """
            The URL to use to load the Swagger UI CSS.

            It is normally set to a CDN URL.
            """
        ),
    ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    swagger_favicon_url: Annotated[
        str,
        Doc(
            """
            The URL of the favicon to use. It is normally shown in the browser tab.
            """
        ),
    ] = "https://fastapi.tiangolo.com/img/favicon.png",
    oauth2_redirect_url: Annotated[
        Optional[str],
        Doc(
            """
            The OAuth2 redirect URL, it is normally automatically handled by FastAPI.
            """
        ),
    ] = None,
    init_oauth: Annotated[
        Optional[Dict[str, Any]],
        Doc(
            """
            A dictionary with Swagger UI OAuth2 initialization configurations.
            """
        ),
    ] = None,
    swagger_ui_parameters: Annotated[
        Optional[Dict[str, Any]],
        Doc(
            """
            Configuration parameters for Swagger UI.

            It defaults to [swagger_ui_default_parameters][fastapi.openapi.docs.swagger_ui_default_parameters].
            """
        ),
    ] = None,
) -> HTMLResponse:
    """
    Generate and return the HTML  that loads Swagger UI for the interactive
    API docs (normally served at `/docs`).

    You would only call this function yourself if you needed to override some parts,
    for example the URLs to use to load Swagger UI's JavaScript and CSS.

    Read more about it in the
    [FastAPI docs for Configure Swagger UI](https://fastapi.tiangolo.com/how-to/configure-swagger-ui/)
    and the [FastAPI docs for Custom Docs UI Static Assets (Self-Hosting)](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/).
    """
    current_swagger_ui_parameters = swagger_ui_default_parameters.copy()
    if swagger_ui_parameters:
        current_swagger_ui_parameters.update(swagger_ui_parameters)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
    <link rel="shortcut icon" href="{swagger_favicon_url}">
    <title>{title}</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{swagger_js_url}"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    {js_patch.replace("TANSTACK_API_CLIENT", tanstack_api_client or "api")}
    const ui = SwaggerUIBundle({{
        url: '{openapi_url}',
        plugins: [
            SwaggerUIBundle.plugins.DownloadUrl,
            SnippedGeneratorNodeJsPlugin
        ],
    """

    for key, value in current_swagger_ui_parameters.items():
        html += f"{json.dumps(key)}: {json.dumps(jsonable_encoder(value))},\n"

    if oauth2_redirect_url:
        html += f"oauth2RedirectUrl: window.location.origin + '{oauth2_redirect_url}',"

    html += """
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
    })"""

    if init_oauth:
        html += f"""
        ui.initOAuth({json.dumps(jsonable_encoder(init_oauth))})
        """

    html += """
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


def patch_fastapi(
    app: FastAPI,
    docs_url: str = "/docs",
    redirect_from_root_to_docs: bool = True,
    *,
    title: Optional[str] = None,
    tanstack_api_client: str | None = None,
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
    :param tanstack_api_client: TanStack API client to use if None will be `import { $api, $apiTypes } from "@/api";`
    :param swagger_js_url: Where to serve Swagger UI JS bundle
    :param swagger_css_url: Where to serve Swagger UI CSS
    :param swagger_favicon_url: Where to serve Swagger UI favicon image - html icon
    :param swagger_ui_parameters: Override parameters for Swagger UI
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
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=title or f"{app.title} - Swagger UI",
            tanstack_api_client=tanstack_api_client,
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
