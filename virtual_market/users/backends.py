from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailModelBackend(ModelBackend):
    """Authentifie l'utilisateur par son adresse e-mail, et uniquement par elle.

    La connexion par nom d'utilisateur est volontairement désactivée : un même
    identifiant ne doit jamais pouvoir ouvrir deux comptes de rôles différents.
    On hérite de ``ModelBackend`` pour conserver la gestion des permissions
    (utilisée par l'administration Django).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # ``username`` est le nom du paramètre attendu par Django/SimpleJWT ;
        # sa valeur correspond à l'e-mail saisi par l'utilisateur.
        identifier = username or kwargs.get("email")
        if not identifier or password is None:
            return None

        user = (
            User.objects.filter(email__iexact=str(identifier).strip())
            .order_by("id")
            .first()
        )
        if user is None:
            # Réduit la fuite d'information par le temps de réponse.
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
