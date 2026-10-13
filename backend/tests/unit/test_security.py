"""Тесты генерации хэша и проверки пароля (src/core/security.py)."""

from src.core.security import hash_password, verify_password


def test_hash_password_returns_bcrypt_hash():
    """Хэш — bcrypt-строка, а не открытый пароль."""
    hashed = hash_password("secret")
    assert hashed.startswith("$2")
    assert hashed != "secret"
    assert len(hashed) > 20


def test_verify_password_correct():
    """Правильный пароль проходит проверку."""
    hashed = hash_password("secret")
    assert verify_password("secret", hashed) is True


def test_verify_password_wrong():
    """Неверный пароль отклоняется."""
    hashed = hash_password("secret")
    assert verify_password("wrong", hashed) is False


def test_hash_is_salted():
    """Одинаковые пароли дают разные хэши (случайная соль)."""
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2


def test_verify_password_empty():
    """Пустой пароль хэшируется и проверяется корректно."""
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("x", hashed) is False


def test_long_passwords_truncated_to_72_bytes():
    """bcrypt работает максимум с 72 байтами; лишние символы отбрасываются.

    Хэширование и проверка обрезают ввод одинаково, поэтому длинные пароли,
    совпадающие в первых 72 байтах, считаются валидными.
    """
    long_pw = "a" * 100
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed) is True
    assert verify_password("a" * 72, hashed) is True
    assert verify_password("a" * 73, hashed) is True
