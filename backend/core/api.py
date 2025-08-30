from ninja import NinjaAPI


api = NinjaAPI(title="Paprika API")


@api.get("/projects/{project_code}/shots/")
def project_shots(request, project_code: str):
    return project_code
