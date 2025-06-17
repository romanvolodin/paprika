from django.contrib.auth.models import Group
from rest_framework import serializers

from core.models import ChatMessage, Project, Shot, ShotGroup, ShotTask, Status, Task, Version
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "avatar",
            "groups",
            "first_name",
            "last_name",
        ]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = "__all__"


class RepliedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ("id", "created_by", "text")


class ChatMessageSerializer(serializers.ModelSerializer):
    reply_to = RepliedMessageSerializer(required=False, allow_null=True)

    class Meta:
        model = ChatMessage
        fields = "__all__"


class ShotSerializer(serializers.ModelSerializer):
    thumb = serializers.SerializerMethodField()
    versions = VersionSerializer(many=True, read_only=True)
    chat_messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Shot
        fields = "__all__"

    def get_thumb(self, shot):
        if not shot.versions.all():
            return

        request = self.context.get("request")
        latest_version = shot.versions.latest()
        return request.build_absolute_uri(latest_version.preview.url)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class ShotGroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShotGroup
        fields = "__all__"


class ShotGroupDetailsSerializer(serializers.ModelSerializer):
    shots = ShotSerializer(many=True, read_only=True)

    class Meta:
        model = ShotGroup
        fields = [
            "id",
            "name",
            "project",
            "is_root",
            "is_default",
            "created_at",
            "created_by",
            "shots",
        ]


class ShotTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShotTask
        fields = "__all__"


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class TaskDetailsSerializer(serializers.ModelSerializer):
    shots = ShotSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "created_at",
            "created_by",
            "description",
            "default_status",
            "shots",
        ]


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"
