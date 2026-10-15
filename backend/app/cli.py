import argparse
import getpass

from app.services.auth_service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Low-Latency Live Video Platform utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "hash-admin-password",
        help="read a password without echoing it and print its scrypt hash",
    )
    args = parser.parse_args()

    if args.command == "hash-admin-password":
        password = getpass.getpass("Administrator password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            parser.error("passwords do not match")
        if len(password) < 12:
            parser.error("administrator password must contain at least 12 characters")
        print(hash_password(password))


if __name__ == "__main__":
    main()
