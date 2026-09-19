from .models import User
from rest_framework import serializers



class UserSerializer(serializers.ModelSerializer):
    # password = serializers.CharField(write_only=True)
    phone = serializers.RegexField(
    regex=r'^\+?\d{8,15}$'
)
    class Meta :
        model = User
        fields = "__all__"

    