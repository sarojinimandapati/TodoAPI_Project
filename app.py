from flask import Flask,request
from flask_restful import Api,Resource
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError
from flask_jwt_extended import JWTManager,jwt_required,create_access_token,get_jwt_identity
from flask_bcrypt import Bcrypt
from datetime import timedelta

app=Flask(__name__)
api=Api(app)

app.config["JWT_SECRET_KEY"]="my secret key" # change in production
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

db=SQLAlchemy(app)
ma=Marshmallow(app)
jwt=JWTManager(app)
bcrypt=Bcrypt(app)
# creating database to store registrations data
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(120),nullable=False)
    password=db.Column(db.String(100),nullable=False)
#databse to store todos data
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(120), nullable=False)
    done = db.Column(db.Boolean, nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey(User.id))

# creating marshmallow database
class TodoSchema(ma.SQLAlchemySchema):
    class Meta: # Using SQLAlchemySchema without 'load_instance=True' means load() returns a dict (not a model instance).
        # The code treats data as a dict (e.g., data["task"]) — that matches current behavior.
        model=Todo
    id=ma.auto_field()
    task=ma.auto_field(required=True)
    done=ma.auto_field()

todo_schema=TodoSchema()
todos_schema=TodoSchema(many=True)

# creating routes for Registration and Login
class Register(Resource):
    def post(self):
        data=request.get_json()
        if not data or not data['username'] or not data['password']:
            return {"message":"both username and password required"},400

        if User.query.filter_by(username=data["username"]).first():
            return {"error": "username already exists"}, 400

        hashed_password=bcrypt.generate_password_hash(data['password'])
        new_user=User(username=data['username'],password=hashed_password)

        db.session.add(new_user)
        db.session.commit()
        return {"message":"User created successfully!..."}

class Login(Resource):
    def post(self):
        data=request.get_json()
        user = User.query.filter_by(username=data.get("username")).first()

        if not user or not bcrypt.check_password_hash(user.password,data['password']):
            return {"message":"Invalid credentials"}

        access_token = create_access_token(identity=str(user.id))# will create a token
        return {"access_token": access_token}, 200

class Todoslist(Resource):
    @jwt_required() # only authorized person can enter
    def get(self):
        user_id=int(get_jwt_identity()) # this will get the identity which is id
        todos=Todo.query.filter_by(user_id=user_id).all()
        return todos_schema.dump(todos),200 # return type should always in json type

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        json_data=request.get_json()

        try :
            data=todo_schema.load(json_data)
        except ValidationError as err:
            return {"error":err.messages}

        todo=Todo(task=data["task"],done=data['done'],user_id=user_id)
        db.session.add(todo)
        db.session.commit()

        return todo_schema.dump(todo),201

class Todoresource(Resource):
   @jwt_required()
   def get(self,todo_id):
       user_id=int(get_jwt_identity())
       data=Todo.query.filter_by(id=todo_id,user_id=user_id).first()

       if not data:
           return {"error": "Todo not found"}, 404

       return todo_schema.dump(data),200

   @jwt_required()
   def put(self,todo_id):
        user_id =int(get_jwt_identity())
        todo = Todo.query.filter_by(id=todo_id, user_id=user_id).first()
        if not todo:
            return {"error": "Todo not found"}, 404

        json_data=request.get_json()

        try:
            data=todo_schema.load(json_data)
        except ValidationError as err:
            return {"error":err.messages},400

        todo.task=data['task']
        todo.done=data['done']

        db.session.commit()
        return todo_schema.dump(todo),200

   @jwt_required()
   def delete(self,todo_id):
       user_id=int(get_jwt_identity())
       todo= Todo.query.filter_by(id=todo_id, user_id=user_id).first()
       if not todo:
           return {"error": "Todo not found"}, 404
       db.session.delete(todo)
       db.session.commit()

       return {"message":"todo deleted"}

api.add_resource(Register,"/register")
api.add_resource(Login,"/login")
api.add_resource(Todoslist,"/todos")
api.add_resource(Todoresource,"/todos/<int:todo_id>")

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)