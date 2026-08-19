from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_db
from app.models import User
from app.core.security import _is_bcrypt_hash, _is_sha256_hex
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service

def test_auth():
    db = next(get_db())

    # 1. Test Seed User Login (roll_number=276804, password=LibraryUser@276804)
    seed_user = db.get(User, "276804")
    assert seed_user is not None, "Seed user 276804 not found"
    initial_hash = seed_user.password_hash
    print(f"Seed user 276804 initial hash: {initial_hash[:20]}... (sha256={_is_sha256_hex(initial_hash)})")

    login_req = LoginRequest(roll_number="276804", password="LibraryUser@276804")
    token_resp = auth_service.login_user(db, login_req)
    print(f"Seed login successful! Token generated for roll_number={token_resp.user.roll_number}")

    # Verify rehash
    db.expire(seed_user)
    updated_user = db.get(User, "276804")
    print(f"Seed user upgraded hash: {updated_user.password_hash[:20]}... (bcrypt={_is_bcrypt_hash(updated_user.password_hash)})")
    assert _is_bcrypt_hash(updated_user.password_hash), "Hash was not rehashed to bcrypt"

    # 2. Test login again with the upgraded bcrypt hash
    token_resp_2 = auth_service.login_user(db, login_req)
    print(f"Subsequent login with bcrypt hash successful!")

    # 3. Test New User Registration
    reg_req = RegisterRequest(
        roll_number="TEST_STUDENT_999",
        name="Test Student",
        email="teststudent999@library.local",
        password="SecretPassword123!"
    )
    try:
        reg_token = auth_service.register_user(db, reg_req)
        print(f"Registration successful for roll_number={reg_token.user.roll_number}")
    except Exception as e:
        print(f"Registration note: {e}")
        login_new = auth_service.login_user(db, LoginRequest(roll_number="TEST_STUDENT_999", password="SecretPassword123!"))
        print(f"Login successful for existing test user: {login_new.user.roll_number}")

    print("\nAll Auth Logic Tests Passed Successfully!")

if __name__ == "__main__":
    test_auth()
