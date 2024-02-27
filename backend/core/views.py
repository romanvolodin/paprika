from django.shortcuts import HttpResponse, render
from openpyxl import load_workbook

from .forms import ReadXlsxForm
from .models import Shot


def read_xlsx(request):
    if request.method == "POST":
        form = ReadXlsxForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "core/xlsx_read.html", {"form": form})

        shot_group = form.cleaned_data["shot_group"]
        created_by = form.cleaned_data["created_by"]
        start_row = form.cleaned_data["start_row"]
        end_row = form.cleaned_data["end_row"]
        shot_name_column = form.cleaned_data["shot_name_column"]

        new_shots = []

        wb = load_workbook(request.FILES["xlsx_file"])
        active_sheet = wb.active
        for row_number in range(start_row, end_row + 1):
            new_shots.append(
                Shot(
                    name=active_sheet[f"{shot_name_column}{row_number}"].value,
                    group=shot_group,
                    created_by=created_by,
                )
            )
        Shot.objects.bulk_create(new_shots)
        return HttpResponse(f"{len(new_shots)} shot(s) created.")
    else:
        form = ReadXlsxForm()
    return render(request, "core/xlsx_read.html", {"form": form})
