from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    jwt_required,
    get_jwt_identity,
)

from db import db
from models import UserModel
from api_schemas import UserSchema
from redis_conn import r

blp = Blueprint("Users", __name__, "The operations on Users")


@blp.route("/register")
class RegisterUser(MethodView):

    @blp.arguments(UserSchema)
    def post(self, user_data):
        user = UserModel(**user_data)
        user.password = pbkdf2_sha256.hash(user.password)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            abort(400, message="A user with this username already exists.")
        except SQLAlchemyError:
            abort(
                500,
                message="An error occured while registering the user. ",
            )
        return {"message": "User created successfully", "status": 1}


@blp.route("/login")
class LoginUser(MethodView):

    @blp.arguments(UserSchema)
    def post(self, user_data):
        user = UserModel.query.filter(
            UserModel.username == user_data["username"]
        ).first()

        if user and pbkdf2_sha256.verify(user_data["password"], user.password):
            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(identity=user.id)
            return {"access_token": access_token, "refresh_token": refresh_token}

        abort(401, message="Invalid username or password ")


@blp.route("/logout")
class UserLogout(MethodView):

    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        r.set(jti, jti)
        return {"message": "Successfully logged out"}


@blp.route("/refresh")
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        jti = get_jwt()["jti"]
        r.set(jti, jti)
        return {"access_token": new_token}, 200
