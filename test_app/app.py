from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from fastapi_swagger import patch_fastapi

app = FastAPI(
    title="Hello, world!",
    docs_url=None,
    swagger_ui_oauth2_redirect_url=None,
)
patch_fastapi(app)


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/some-data")
async def some_data(
    data: str | None = None, a: int | None = None, b: int | None = None
):
    return JSONResponse({"message": "Some data!", "data": data, "a": a, "b": b})


class SomeData(BaseModel):
    data: str | None = None
    a: int | None = None
    b: int | None = None


@app.post("/some-data")
async def some_data_post(
    body: SomeData,
    in_path_data: str | None = None,
):
    return JSONResponse(
        {"message": "Some data!", "data": body.data, "a": body.a, "b": body.b}
    )


@app.get("/error")
async def error():
    raise Exception("This is a test error")
