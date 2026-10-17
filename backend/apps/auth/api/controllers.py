from typing import TypeVar

from dmr import Controller
from dmr.security import AuthenticatedHttpRequest
from dmr.serializer import BaseSerializer

from apps.users.models import User

from .security import access_token_auth


_SerializerT = TypeVar("_SerializerT", bound=BaseSerializer)


class AuthenticatedController(Controller[_SerializerT]):
    """Base for every API controller that needs a logged-in user.

    Authentication is on by default, so a new controller cannot become
    public by forgetting to declare ``auth``. The only public controllers
    are the ones in ``apps.auth.api.views`` (login and refresh), which do
    not inherit from this class.

    This class is abstract: it has no HTTP methods and is never routed.
    Pick the serializer when subclassing, e.g.
    ``AuthenticatedController[PydanticSerializer]``.
    """

    request: AuthenticatedHttpRequest[User]
    auth = (access_token_auth,)
