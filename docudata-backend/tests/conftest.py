import os

from cryptography.fernet import Fernet


os.environ.setdefault("DOCUDATA_APP_SECRET", "chave-de-aplicacao-para-testes")
os.environ.setdefault("ALLOWED_ORIGINS", "https://frontend.test,http://localhost:3000")
os.environ.setdefault("DOCUDATA_SECRETS_KEY", Fernet.generate_key().decode("utf-8"))
