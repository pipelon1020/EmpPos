from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=5)
    name: str = Field(min_length=2)       
    password: str = Field(min_length=4)
    is_admin: bool = False                
    active: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "pipelon1020",
                "name": "Daniel",
                "password": "1031",
                "is_admin": False,
                "active": True
            }
        }
    }

class UserOut(BaseModel): #Modelo para devolver user
    username: str
    name: str
    is_admin: bool
    active: bool

    model_config = {"from_attributes": True}

class ChangeUsername(BaseModel):
    new_username: str = Field(min_length=5)

class ChangePassword(BaseModel):
    current_password: str = Field(min_length=4)  # para verificar antes de cambiar
    new_password: str = Field(min_length=4)