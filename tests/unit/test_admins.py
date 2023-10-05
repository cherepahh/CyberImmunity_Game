from src.admins import check_authorization, _force_admin_usernames

def test_admin():
    admin_usernames = "admin"
    _force_admin_usernames(admin_usernames)
    is_authorized = check_authorization("admin")
    assert is_authorized

    admin_usernames = "admin1, admin2"
    _force_admin_usernames(admin_usernames)
    is_authorized = check_authorization("admin1")
    assert is_authorized
    is_authorized = check_authorization("admin2")
    assert is_authorized
    is_authorized = check_authorization("admin3")
    assert is_authorized is False
