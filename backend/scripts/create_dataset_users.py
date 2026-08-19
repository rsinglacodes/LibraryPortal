import pandas as pd
import hashlib
from pathlib import Path


# --------------------------------------------------
# Paths
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_PATH = SCRIPT_DIR.parent / "data" / "library_combined_dataset.csv"


# --------------------------------------------------
# Load dataset
# --------------------------------------------------

df = pd.read_csv(DATASET_PATH)

print(f"Loaded dataset: {len(df):,} rows")
print(f"Unique users: {df['user_id'].nunique():,}")


# --------------------------------------------------
# Generate synthetic user information
# --------------------------------------------------

def generate_user_data(user_id):
    """
    Generate deterministic synthetic data for a user.

    The same user_id will always produce the same
    name, email, and password.
    """

    user_id = str(user_id)

    name = f"User {user_id}"

    email = f"user{user_id}@library.local"

    # Deterministic synthetic password
    raw_password = f"LibraryUser@{user_id}"
    password = hashlib.sha256(
        raw_password.encode("utf-8")
    ).hexdigest()

    return name, email, password


# --------------------------------------------------
# Create mapping for unique users
# --------------------------------------------------

unique_users = df["user_id"].drop_duplicates()

user_data = {}

for user_id in unique_users:
    name, email, password = generate_user_data(user_id)

    user_data[user_id] = {
        "name": name,
        "email": email,
        "password": password
    }


# --------------------------------------------------
# Add synthetic columns to the original dataset
# --------------------------------------------------

df["name"] = df["user_id"].map(
    lambda user_id: user_data[user_id]["name"]
)

df["email"] = df["user_id"].map(
    lambda user_id: user_data[user_id]["email"]
)

df["password"] = df["user_id"].map(
    lambda user_id: user_data[user_id]["password"]
)


# --------------------------------------------------
# Save back to THE SAME CSV
# --------------------------------------------------

df.to_csv(DATASET_PATH, index=False)


# --------------------------------------------------
# Verification
# --------------------------------------------------

print("\nSynthetic user data added successfully.")

print(f"Dataset saved to:")
print(DATASET_PATH)

print("\nNew columns:")
print(["name", "email", "password"])

print("\nSample:")
print(
    df[
        [
            "user_id",
            "name",
            "email",
            "password"
        ]
    ].drop_duplicates("user_id").head(10).to_string(index=False)
)

print("\nFinal dataset shape:")
print(df.shape)