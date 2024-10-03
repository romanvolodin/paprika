from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import HttpResponse, render
from openpyxl import load_workbook

from .forms import ReadXlsxForm, UploadMultiplePreviewsForm
from .models import Project, Shot, ShotGroup, TmpShotPreview


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
        rec_timecode_column = form.cleaned_data["rec_timecode_column"]
        src_name_column = form.cleaned_data["source_name_column"]
        src_start_tc_column = form.cleaned_data["source_start_timecode_column"]
        src_end_tc_column = form.cleaned_data["source_end_timecode_column"]
        pixel_aspect_column = form.cleaned_data["pixel_aspect_column"]
        retime_speed_column = form.cleaned_data["retime_speed_column"]
        scene_column = form.cleaned_data["scene_column"]

        new_shots = []

        wb = load_workbook(request.FILES["xlsx_file"])
        active_sheet = wb.active
        for row_number in range(start_row, end_row + 1):
            fields = {
                "group": shot_group,
                "created_by": created_by,
            }

            name = active_sheet[f"{shot_name_column}{row_number}"].value
            fields["name"] = name

            rec_timecode = active_sheet[f"{rec_timecode_column}{row_number}"].value
            if rec_timecode is not None:
                fields["rec_timecode"] = rec_timecode

            source_name = active_sheet[f"{src_name_column}{row_number}"].value
            if source_name is not None:
                fields["source_name"] = source_name

            source_start_timecode = active_sheet[f"{src_start_tc_column}{row_number}"].value
            if source_start_timecode is not None:
                fields["source_start_timecode"] = source_start_timecode

            source_end_timecode = active_sheet[f"{src_end_tc_column}{row_number}"].value
            if source_end_timecode is not None:
                fields["source_end_timecode"] = source_end_timecode

            pixel_aspect = active_sheet[f"{pixel_aspect_column}{row_number}"].value
            if pixel_aspect is not None:
                fields["pixel_aspect"] = pixel_aspect if isinstance(pixel_aspect, float) else 1

            retime_speed = active_sheet[f"{retime_speed_column}{row_number}"].value
            fields["retime_speed"] = retime_speed
            if retime_speed is None:
                fields["retime_speed"] = 100

            scene = active_sheet[f"{scene_column}{row_number}"].value
            if scene is not None:
                fields["scene"] = scene

            new_shots.append(Shot(**fields))
        Shot.objects.bulk_create(new_shots)
        return HttpResponse(f"{len(new_shots)} shot(s) created.")
    else:
        form = ReadXlsxForm()
    return render(request, "core/xlsx_read.html", {"form": form})


def save_multiple_uploaded_shot_previews(request):
    if request.method == "POST":
        form = UploadMultiplePreviewsForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "core/upload_multiple_shot_previews.html", {"form": form})

        previews = form.cleaned_data["previews"]
        successful_count = 0
        errors = []
        for preview in previews:
            shot_name = preview.name.split(".")[0]

            if shot_name is None:
                errors.append(f"Нет имени шота в '{preview.name}'")
                continue

            try:
                shot = Shot.objects.get(name=shot_name)
            except ObjectDoesNotExist:
                errors.append(f"Шот '{shot_name}' не найден")
                continue

            TmpShotPreview.objects.create(shot=shot, image=preview)
            successful_count += 1
        return HttpResponse(
            f"{successful_count} картинок загружено.<br><br>Ошибки:<br>{'<br>'.join(errors)}"
        )
    else:
        form = UploadMultiplePreviewsForm()
    return render(request, "core/upload_multiple_shot_previews.html", {"form": form})


def shot_group_list(request, project_code):
    project = Project.objects.get(code=project_code)
    context = {"shot_groups": project.shot_groups.all().order_by("name")}
    return render(request, "core/shot_group_list.html", context)


def shot_group_details(request, project_code, shot_group_id):
    shot_group = ShotGroup.objects.get(pk=shot_group_id)
    context = {
        "shot_group": shot_group,
    }
    return render(request, "core/shot_group_details.html", context)
