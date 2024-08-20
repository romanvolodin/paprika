from django import forms
from users.models import User

from .models import Shot, ShotGroup


class ReadXlsxForm(forms.Form):
    xlsx_file = forms.FileField()
    shot_group = forms.ModelChoiceField(ShotGroup.objects.all())
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
