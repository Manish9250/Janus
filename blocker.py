import os
from app_terminator import close_all_browsers


# Python script to block distracting websites by modifying the /etc/hosts file.

HOSTS_PATH = "/etc/hosts"
JANUS_START_MARKER = "# START JANUS BLOCKLIST\n"
JANUS_END_MARKER = "# END JANUS BLOCKLIST\n"

distracting_sites = []

def block_sites(distracting_sites: list = distracting_sites):
    print("Blocking distracting sites...")
    # First, make sure we don't have a previous block active
    unblock_sites(silent=True)

    with open(HOSTS_PATH, "a") as hosts_file:
        hosts_file.write(JANUS_START_MARKER)
        for site in distracting_sites:
            hosts_file.write(f"127.0.0.1 {site}\n")
        hosts_file.write(JANUS_END_MARKER)
    
    # Flush DNS cache
    #os.system("sudo systemd-resolve --flush-caches")
    print("Sites blocked.")
    close_all_browsers()


def unblock_sites(silent=False):
    if not silent:
        print("Unblocking distracting sites...")
    
    try:
        with open(HOSTS_PATH, "r") as f:
            lines = f.readlines()

        with open(HOSTS_PATH, "w") as f:
            in_janus_block = False
            for line in lines:
                if line.strip() == JANUS_START_MARKER.strip():
                    in_janus_block = True
                    continue
                if line.strip() == JANUS_END_MARKER.strip():
                    in_janus_block = False
                    continue
                if not in_janus_block:
                    f.write(line)

        # Flush DNS cache
        #os.system("sudo systemd-resolve --flush-caches")
        if not silent:
            print("Sites unblocked.")

    except FileNotFoundError:
        print(f"Error: {HOSTS_PATH} not found.")


def block_for_duration(duration: int, distracting_sites: list = distracting_sites):
    import time
    block_sites(distracting_sites)
    time.sleep(duration)
    unblock_sites()

if __name__ == "__main__":
    # Example usage
    distracting_sites = ["facebook.com", "www.youtube.com", "twitter.com", "www.instagram.com"]
    block_for_duration(600, distracting_sites)  # Block for 10 minutes
    #unblock_sites()  # Uncomment to unblock immediately
