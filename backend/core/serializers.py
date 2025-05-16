from django.contrib.auth.models import Group
from rest_framework import serializers

from core.models import Project, Shot, ShotGroup, ShotTask, Status, Task, Version
from users.models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "email", "avatar", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class VersionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Version
        fields = "__all__"


class ShotSerializer(serializers.HyperlinkedModelSerializer):
    thumb = serializers.SerializerMethodField()
    versions = VersionSerializer(many=True, read_only=True)

    class Meta:
        model = Shot
        fields = "__all__"

    def get_thumb(self, shot):
        if not shot.versions.all():
            return

        request = self.context.get("request")
        latest_version = shot.versions.latest()
        return request.build_absolute_uri(latest_version.preview.url)


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class ShotGroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ShotGroup
        fields = "__all__"


class ShotTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ShotTask
        fields = "__all__"


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class StatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"
