"""Traffic weights + graceful reload; no image rebuild or container restart."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ROUTE_FILE = ROOT / "routing" / "active-upstream.conf"


def upstream(percent: int) -> str:
    if percent not in {0, 5, 25, 50, 100}:
        raise ValueError("Allowed canary percentages: 0, 5, 25, 50, 100")
    servers = []
    if percent < 100:
        servers.append(f"    server stable:8000 weight={100 - percent};")
    if percent > 0:
        servers.append(f"    server canary:8000 weight={percent};")
    return "upstream inference_pool {\n" + "\n".join(servers) + "\n}\n"


def change_route(percent: int, *, docker: bool = True) -> None:
    previous = ROUTE_FILE.read_text(encoding="utf-8")
    new_value = upstream(percent)
    tmp = ROUTE_FILE.with_suffix(".tmp")
    tmp.write_text(new_value, encoding="utf-8")
    os.replace(tmp, ROUTE_FILE)
    if docker:
        try:
            subprocess.run(["docker", "compose", "exec", "-T", "gateway", "nginx", "-t"],
                           cwd=ROOT, check=True)
            subprocess.run(["docker", "compose", "exec", "-T", "gateway", "nginx", "-s", "reload"],
                           cwd=ROOT, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            recovery = ROUTE_FILE.with_suffix(".recovery")
            recovery.write_text(previous, encoding="utf-8")
            os.replace(recovery, ROUTE_FILE)
            subprocess.run(["docker", "compose", "exec", "-T", "gateway", "nginx", "-s", "reload"],
                           cwd=ROOT, check=False)
            raise
    print(f"ROUTE_CHANGED stable={100 - percent}% canary={percent}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("canary_percent", type=int, choices=[0, 5, 25, 50, 100])
    parser.add_argument("--no-reload", action="store_true",
                        help="Write initial route before containers are started")
    args = parser.parse_args()
    change_route(args.canary_percent, docker=not args.no_reload)

if __name__ == "__main__":
    main()
