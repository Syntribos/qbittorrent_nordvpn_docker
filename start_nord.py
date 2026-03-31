import sys
import time
from argparse import ArgumentParser

from utils.custom_types import NordException
from utils.nord import Nord
from utils.return_value import ReturnCode, ReturnObject


def init_nord(login_token: str, retries: int) -> int:
    nord = Nord()
    result = ReturnObject(ReturnCode.FAILURE)
    for i in range(0, retries):
        if i != 0:
            print(f"Trying again. Attempt {i + 1}...")
        result = nord.try_login(login_token)
        if result.return_code is ReturnCode.SUCCESS or "already logged" in result.out_str():
            break
        print("Login failed.")
        time.sleep(3)

    result.raise_if_err(exception_type=NordException, default_message="Couldn't log into Nord.")

    result = nord.try_connect(retries)
    result.raise_if_err(
        exception_type=NordException, default_message=f"Couldn't connect to Nord after {retries + 1} tries."
    )
    print("Finished Nord setup.")
    return 0


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        '-t',
        '--token',
        type=str,
        required=True,
        help="The login token for NordVPN. Should be a 64 character string."
    )
    parser.add_argument(
        '-r',
        "--retries",
        type=int,
        required=False,
        default=5
    )
    args = parser.parse_args()

    if token := args.token:
        return init_nord(token, args.retries or 5)
    return 1


if __name__ == "__main__":
    sys.exit(main())
