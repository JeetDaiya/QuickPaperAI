server/
├── core/                         # 🆕 Create this folder for config and security helpers
│   ├── config.py                 # JWT Secret Keys, token expiration times, etc.
│   └── security.py               # Hashing passwords (bcrypt) and creating/verifying JWTs
│
├── schemas/                      # 🆕 Create this folder for input/output data validation
│   ├── __init__.py
│   ├── user_schemas.py           # UserRegister, UserLogin, UserResponse Pydantic models
│   └── token_schemas.py          # Token and TokenData models
│
└── routes/
    ├── auth_routes.py            # 🆕 Create this for signup, login, and user profile endpoints
    ├── db_routes.py
    └── paper_routes.py
