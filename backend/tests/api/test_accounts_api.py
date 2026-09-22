from tests.conftest import client, seed_test_db


def setup_function():
    seed_test_db()


def test_create_account_returns_canonical_role():
    response = client.post(
        "/api/companies/1/accounts",
        json={
            "code": "TOTAL-ACTIVO",
            "name": "Activo",
            "account_type": "ACTIVO",
            "canonical_role": "ACTIVO",
        },
    )

    assert response.status_code == 201
    assert response.json()["canonical_role"] == "ACTIVO"
