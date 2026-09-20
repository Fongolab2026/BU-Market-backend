from rest_framework import serializers


class ModerationItemSerializer(serializers.Serializer):
    """Élément de la file de modération : { id, type, title, owner, date, status }"""

    id = serializers.IntegerField(read_only=True)
    type = serializers.SerializerMethodField()
    title = serializers.CharField(source="username", read_only=True)
    owner = serializers.CharField(source="username", read_only=True)
    date = serializers.DateTimeField(source="date_joined", read_only=True)
    status = serializers.SerializerMethodField()

    def get_type(self, obj):
        return "seller"

    def get_status(self, obj):
        return "pending"