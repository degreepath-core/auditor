def pytest_addoption(parser):
    parser.addoption(
        '--update-snapshots',
        action='store_true',
        default=False,
        help='rewrite fixture snapshots in fixtures/snapshots/ instead of comparing against them',
    )
