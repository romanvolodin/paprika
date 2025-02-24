from django import forms

from users.models import User

from .models import Project, ShotGroup, Task


class ReadXlsxForm(forms.Form):
    xlsx_file = forms.FileField()
    # shot_group = forms.ModelChoiceField(ShotGroup.objects.all())
    created_by = forms.ModelChoiceField(User.objects.all())
    start_row = forms.IntegerField(help_text="(Int)")
    end_row = forms.IntegerField(help_text="(Int)")
    shot_name_column = forms.CharField(help_text="(A,B,C,...)")
    rec_timecode_column = forms.CharField(help_text="(A,B,C,...)")
    source_name_column = forms.CharField(help_text="(A,B,C,...)")
    source_start_timecode_column = forms.CharField(help_text="(A,B,C,...)")
    source_end_timecode_column = forms.CharField(help_text="(A,B,C,...)")
    pixel_aspect_column = forms.CharField(help_text="(A,B,C,...)")
    retime_speed_column = forms.CharField(help_text="(A,B,C,...)")
    scene_column = forms.CharField(help_text="(A,B,C,...)")


class AddShotsToGroupsForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    groups = forms.ModelMultipleChoiceField(ShotGroup.objects.all())


class AddTasksToShotForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    tasks = forms.ModelMultipleChoiceField(Task.objects.all())


class AddСommentToShotForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    created_by = forms.ModelChoiceField(User.objects.all())
    comment = forms.CharField(help_text="Комментарий длиной до 255 символов")


class AddShotsToProjectForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    project = forms.ModelChoiceField(Project.objects.all())


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class UploadMultiplePreviewsForm(forms.Form):
    previews = MultipleFileField()


class UploadMultipleVersionsForm(forms.Form):
    versions = MultipleFileField()
