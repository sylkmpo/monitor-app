from security import create_access_token, decode_token_subject


def test_access_token_round_trip_subject():
    token = create_access_token({"sub": "admin", "role": "admin"})

    assert decode_token_subject(token) == "admin"
