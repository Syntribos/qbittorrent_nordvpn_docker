import sys
import time

from utils.liveness_checker import LivenessChecker
from utils.nord import Nord


def main() -> int:
    result = LivenessChecker(Nord()).start()

    # If we got here, the liveness check failed for a while
    # Wait 10 mins to clear out rate limits
    time.sleep(60 * 10)
    return result


if __name__ == '__main__':
    sys.exit(main())
