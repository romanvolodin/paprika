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


class ChatMessageSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = "__all__"

    def get_reply_to(self, obj):
        if hasattr(obj, "reply_to") and obj.reply_to:
            message = ChatMessageSerializer(obj.reply_to).data
            created_by = message["created_by"]
            return {
                "id": message["id"],
                "text": message["text"],
                "created_by": f"{created_by['first_name']} {created_by['last_name']}",
            }


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


class ShotGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShotGroup
        fields = "__all__"


class ShotTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShotTask
        fields = "__all__"


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"
