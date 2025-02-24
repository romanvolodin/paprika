from django.contrib.auth.models import Group
from rest_framework import serializers
from users.models import User
from core.models import Shot, Project, ShotGroup, ShotTask, Task, Status


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "email", "avatar", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class ShotSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Shot
        fields = "__all__"


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