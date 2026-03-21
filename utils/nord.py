import time

from utils.command_runner import CommandRunner
from utils.custom_types import NordException
from utils.return_value import ReturnCode, ReturnObject, StdResult


class Nord(CommandRunner):
    def try_login(self, token: str) -> ReturnObject[StdResult]:
        result = self.run_command("/etc/init.d/nordvpn start")
        if result.return_code != ReturnCode.SUCCESS:
            raise Exception("Couldn't start nord")
        time.sleep(5)
        print("Running command nordvpn login --token [HIDDEN]")
        return self.run_command(f"nordvpn login --token {token}", log_command=False)

    def try_connect(self, retries: int) -> ReturnObject[str]:
        print("Connecting...")
        _ = self.run_command("nordvpn set killswitch off")
        _ = self.run_command("nordvpn set lan-discovery enabled")

        try:
            self.reset_nord(False, retries, True)
        except:
            return ReturnObject(ReturnCode.FAILURE, f"Couldn't connect to nord after {retries + 1} tries.")
        return ReturnObject(ReturnCode.SUCCESS)

    def reset_nord(self, do_disconnect: bool = True, connect_retries: int = 0, kill_network_until_connection_established: bool = False) -> None:
        print(f"{'Resetting' if do_disconnect else 'Starting'} Nord...")
        if do_disconnect:
            _ = self.run_command("nordvpn disconnect")
        time.sleep(5)

        result = self.run_command("nordvpn connect p2p")

        if result.return_code is not ReturnCode.SUCCESS:
            for _ in range(connect_retries):
                print(f"Connection error: {result.err_str()}")
                print("Couldn't connect. Waiting 30 seconds.")
                time.sleep(30)
                result = self.run_command("nordvpn connect p2p")
                if result.return_code is ReturnCode.SUCCESS:
                    break
        result.raise_if_err(exception_type=NordException, default_message="nordvpn connect p2p failed.")

        _ = self.run_command("nordvpn set killswitch on")

        if kill_network_until_connection_established:
            _ = self.run_command("ip route del default")

        # Wait for nordlynx to come back up
        for _ in range(30):
            result = self.run_command("ip link show nordlynx")
            result.raise_if_err(exception_type=NordException, default_message="nordvpn connect p2p failed.")
            result_str = result.out_str()
            if "nordlynx" in result_str and "LOWER_UP" in result_str:
                time.sleep(10)  # settle time
                print("nordlynx back up.")
                _ = self.run_command("ip route del default table 205 2>/dev/null || true")
                _ = self.run_command("ip route add default via 10.5.0.1 dev nordlynx table 205")
                if kill_network_until_connection_established:
                    _ = self.run_command("ip route add default via 172.18.0.1 dev eth0")
                return
            time.sleep(5)
        raise Exception("nordlynx did not come back up after reconnect. Killing self to trigger restart.")
