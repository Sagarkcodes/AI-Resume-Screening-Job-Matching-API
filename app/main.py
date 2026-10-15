from fastapi import FastAPI, Depends, HTTPException, Request


from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.db.session import get_db

from app.api.routes.auth import router as auth_router

from app.api.routes.resumes import router as resumes_router

from app.api.routes.jobs import router as jobs_router

from app.api.routes.matches import router as matches_router

from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.web.routes import router as web_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AN API for resume screening and job matching.",
)


BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


#Browser route
app.include_router(web_router)


#Register the authentication routes
app.include_router(auth_router)

#Register resume routes
app.include_router(resumes_router)

#register job management routes
app.include_router(jobs_router)

#Register matching route
app.include_router(matches_router)



@app.get("/health")
def health_check():
    return{
        "status":"healthy",
        "application":settings.APP_NAME
   }
    
     
@app.get("/health/database")
def database_health_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("SELECT current_database(), current_user")
        )
        database, user = result.fetchone()
        
        return{
            "status": "connected",
            "database": database,
            "user": user,
        }
        
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database is currently unavailable."
        )
        
 
@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={},
    ) 

@app.get("/layout-test", include_in_schema=False)
def layout_test(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="layout_test.html",
        context={},
    )     
       

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Use an OpenAPI version compatible with Swagger UI file pickers.
    schema["openapi"] = "3.0.3"

    components = schema.get("components", {}).get("schemas", {})

    for component in components.values():
        properties = component.get("properties", {})

        for prop in properties.values():
            # Fix multiple-file upload fields.
            if prop.get("type") == "array":
                items = prop.get("items", {})

                if items.get("contentMediaType") == "application/octet-stream":
                    items.pop("contentMediaType", None)
                    items["format"] = "binary"

            # Fix single-file upload fields.
            elif (
                prop.get("type") == "string"
                and prop.get("contentMediaType") == "application/octet-stream"
            ):
                prop.pop("contentMediaType", None)
                prop["format"] = "binary"

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
