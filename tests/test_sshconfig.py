from fox.sshconfig import match


def test_match():
    tests = [
        ("example.com", ["*.com"], True),
        ("example.com", ["*.org"], False),
        ("web.example.com", ["*.example.co?"], True),
        ("web.example.com", ["*.net", "*.???"], True),
        ("web.example.com", ["*.net", "*.??g"], False),
        ("web.example.com", ["*.net", "!*.com", "*.example.com"], False),
    ]

    for hostname, patterns, result in tests:
        assert match(hostname, patterns) == result
