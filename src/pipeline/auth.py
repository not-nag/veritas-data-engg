"""Firebase ID-token verification at the API boundary, including direct API calls."""
import os
from . import settings

class Unauthorized(ValueError):
    pass

def identity(authorization):
    required = os.getenv('VERITAS_REQUIRE_AUTH', 'false').lower() == 'true'
    if not required:
        return 'local-developer'
    project = os.getenv('FIREBASE_PROJECT_ID', '')
    if not project:
        raise Unauthorized('Sign-in is not configured. Writes are disabled.')
    if not authorization or not authorization.startswith('Bearer '):
        raise Unauthorized('Sign in to upload or change data.')
    try:
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request
        claims = id_token.verify_firebase_token(authorization[7:], Request(), audience=project)
        if claims.get('iss') != f'https://securetoken.google.com/{project}' or claims.get('aud') != project:
            raise ValueError('Incorrect token issuer or audience')
        uid = claims.get('sub')
        provider = claims.get('firebase', {}).get('sign_in_provider')
        if not uid or provider in (None, 'anonymous'):
            raise ValueError('Interactive sign-in required')
        return uid
    except Exception:
        raise Unauthorized('Your sign-in has expired or is invalid. Please sign in again.') from None
