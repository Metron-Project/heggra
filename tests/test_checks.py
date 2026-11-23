from heggra.checks import AUTHENTICATION_MIDDLEWARE, check_login_required, check_storage


def test_storage_ok():
    assert check_storage(None) == []


def test_storage_missing(settings):
    settings.HEGGRA_STORAGE = "uploads"
    [error] = check_storage(None)
    assert error.id == "heggra.E001"


def test_login_required_off():
    assert check_login_required(None) == []


def test_login_required_by_default_without_middleware(settings):
    del settings.HEGGRA_LOGIN_REQUIRED
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if m != AUTHENTICATION_MIDDLEWARE]
    [warning] = check_login_required(None)
    assert warning.id == "heggra.W001"


def test_login_required_with_middleware(settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    assert check_login_required(None) == []


def test_login_required_without_middleware(settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if m != AUTHENTICATION_MIDDLEWARE]
    [warning] = check_login_required(None)
    assert warning.id == "heggra.W001"
