import logging

from ninja.security import HttpBearer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            validated_token = AccessToken(token)
            user_id = validated_token.get("user_id")
            if not user_id:
                logger.warning("No user_id in token")
                return None

            user = User.objects.get(id=user_id)
            logger.info(f"Authenticated user: {user}")

            return user, token

        except (InvalidToken, TokenError) as e:
            logger.error(f"JWT Error: {e}")
            return None
        except User.DoesNotExist:
            logger.error("User not found")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
