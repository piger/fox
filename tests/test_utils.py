from fox.utils import split_lines


def test_split_lines():
    tests = [
        ("ciao\na\nte", (["ciao", "a"], "te")),
        ("ciao\na\nte\n", (["ciao", "a", "te"], "")),
    ]

    for data, expected in tests:
        lines, rest = split_lines(data)
        assert lines == expected[0]
        assert rest == expected[1]
