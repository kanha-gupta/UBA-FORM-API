from API.utils.Auth import Auth
from ..models.AuthSchema import UserOut, UserAuth
from ..models.RequestBodySchema import FormData
from ..models.AuthSchema import TokenPayload, SystemUser
from ..utils.DBQueries import DBQueries
from ..core.ConfigEnv import settings

from fastapi.responses import RedirectResponse
from fastapi import Depends, HTTPException, status
from pydantic import ValidationError

from jose import jwt

from datetime import datetime, timedelta
from typing import Dict, Optional, Any


def signup(response_result, data: UserAuth):
    # querying database to check if user already exist
    user = DBQueries.filtered_db_search("Auth", data.role, [], AADHAR=data.AADHAR_NO)
    if len(list(user)) != 0:
        response_result['status'] = f'failed'
        response_result['message'].append(f'User with this AADHAR NO already exist')
    else:
        userinfo = {
            'AADHAR': data.AADHAR_NO,
            'password': Auth.get_password_hash(data.password),
            'village_name': data.village_name,
        }
        DBQueries.insert_to_database("Auth", data.role, userinfo)  # saving user to database
        response_result['status'] = f'success'
        response_result['message'].append(f'User with this AADHAR NO created successfully')


def user_login(tokens, form_data: UserAuth):
    user = DBQueries.filtered_db_search("Auth", form_data.role, ['_id'], AADHAR=form_data.AADHAR_NO)
    data = list(user)
    if len(data) is 0:
        tokens['status'] = 'login failed'
    else:

        if not Auth.verify_password(form_data.password, data[0]['password']):
            tokens['status'] = 'login failed'

        else:
            tokens['access_token'] = Auth.create_access_token(form_data.AADHAR_NO)
            tokens['refresh_token'] = Auth.create_refresh_token(form_data.AADHAR_NO)
            tokens['status'] = 'login successful'
            tokens['role'] = form_data.role


async def get_current_user(token: str = Depends()) -> SystemUser:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        print(token_data.sub)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except(jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cursor = DBQueries.filtered_db_search("Auth", "admin", ['_id'], AADHAR=token_data.sub)
    user: Optional[Dict[str, Any]] = list(cursor)[0]
    print(user)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    return SystemUser(**user)
