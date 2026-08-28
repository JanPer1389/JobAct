from jobact.contexts.identity.infrastructure.password_hasher import (
    Argon2idPasswordHasher,
)


async def test_argon2id_hasher_round_trip_and_dummy_verification() -> None:
    hasher = Argon2idPasswordHasher()
    encoded = await hasher.hash("correct horse battery staple")

    assert encoded.startswith("$argon2id$")
    assert await hasher.verify("correct horse battery staple", encoded) is True
    assert await hasher.verify("wrong password", encoded) is False
    assert await hasher.verify("wrong password", None) is False
