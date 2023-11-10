import os
import re
import sys


# Function to initialize logging
def initialize_logging():
    logs_folder = "LOG"
    os.makedirs(logs_folder, exist_ok=True)
    log_file_path = os.path.join(logs_folder, "logs.txt")

    # Redirect standard output to the log file
    sys.stdout = open(log_file_path, "w")
    print(f"Logging started. Log file: {log_file_path}")


# Function to read MAC address and corresponding port information from a log file
def read_mac_port_hashmap(mac_add_file):
    with open(mac_add_file, 'r') as file:
        log_contents = file.read()

    # Use regular expressions to extract MAC address, entry type (STATIC or DYNAMIC), and port
    mac_port_entries = re.findall(r"(\d+)\s+(\w+\.\w+\.\w+)\s+(STATIC|DYNAMIC)\s+(\S+)", log_contents)

    # Create a dictionary (hashmap) where MAC addresses are keys and ports are values
    # Modify port names based on prefixes: Fi -> FiveGigabitEthernet, Gi -> GigabitEthernet
    mac_port_hashmap = {}
    for vlan, mac, entry_type, port in mac_port_entries:
        if port.startswith("Fi"):
            port = "FiveGigabitEthernet" + port[2:]
        elif port.startswith("Gi"):
            port = "GigabitEthernet" + port[2:]
        mac_port_hashmap[mac] = port

    return mac_port_hashmap


# Function to extract interface configurations from a config text using regular expressions
def extract_interfaces(config_text, old_mac_port_hashmap, new_mac_port_hashmap):
    # Define a regular expression pattern to match interface configurations
    interface_pattern = r'interface GigabitEthernet(\d+)/0/(\d+)(.*?)\!'
    matches = re.finditer(interface_pattern, config_text, re.DOTALL)
    extracted_config = {}
    count = 0

    # Iterate through the matched interface configurations
    for match in matches:
        interface_group = int(match.group(1))
        current_interface = f"GigabitEthernet{interface_group}/0/{match.group(2)}"
        port_no = str(interface_group) + "/0/" + str(match.group(2))
        interface_config = match.group(3).strip()

        # Check if the current interface is in the old MAC address to port hashmap
        for mac, port in old_mac_port_hashmap.items():
            old_port_no = re.search(r'\d+/\d+/\d+', port).group()
            if port_no == f"{old_port_no}":
                # Check if the MAC address is in the new MAC address hashmap
                new_port = new_mac_port_hashmap.get(mac)
                if new_port is not None:
                    print(f"Found MAC address in 3850 {mac} - {port}. On 9300 port is {new_port}.")
                    extracted_config[current_interface] = interface_config
                    count += 1
                    break
    print("Total Count: ", count)
    return extracted_config


# Function to save extracted interface configurations to a file
def save_config_to_file(extracted_config, output_file):
    with open(output_file, "w") as file:
        for interface, config in extracted_config.items():
            file.write(f"Interface {interface}\n")
            config_lines = config.strip().split('\n')
            for line in config_lines:
                file.write(line.strip() + '\n')
            file.write("!\n")


# Function to replace old port numbers with new port numbers in a config text
def replace_port_numbers(config_text, old_port_to_mac, new_port_to_mac):
    count = 0
    updated_config = config_text
    # Iterate through the old MAC address to port hashmap
    for old_mac, old_port in old_port_to_mac.items():
        new_port = new_port_to_mac.get(old_mac)
        if new_port:
            # Use regular expression to match whole words
            pattern = re.compile(r'\b' + re.escape(old_port) + r'\b')
            updated_config = pattern.sub(new_port, updated_config)
            print(f"Replaced {old_port} with {new_port}")
            count += 1
    print("Total Count: ", count)
    return updated_config


if __name__ == "__main__":

    initialize_logging()

    # List MAC_ADD and CONFIG files
    mac_add_files = [file for file in os.listdir("MAC_ADD") if "3850" in file]
    config_files = [file for file in os.listdir("CONFIG") if "3850" in file]

    # Build the old_mac_port_hashmap and new_mac_port_hashmap dictionaries
    old_mac_port_hashmap = {}
    new_mac_port_hashmap = {}
    for old_mac_add_file in mac_add_files:
        old_mac_port_hashmap.update(read_mac_port_hashmap(os.path.join("MAC_ADD", old_mac_add_file)))
        new_mac_add_file = next(
            (file for file in os.listdir("MAC_ADD") if "9300" in file and file[:3] == old_mac_add_file[:3]), None)
        if new_mac_add_file:
            new_mac_port_hashmap.update(read_mac_port_hashmap(os.path.join("MAC_ADD", new_mac_add_file)))

    # Process config_files after building the dictionaries
    for old_config_file in config_files:
        input_file = os.path.join("CONFIG", old_config_file)
        output_file_prefix = input_file.split(".")[0]
        extracted_config_file = "extracted_config.txt"

        with open(input_file, "r") as file:
            config_text = file.read()
            print(f"Reading configuration from {input_file}")

        extracted_config = extract_interfaces(config_text, old_mac_port_hashmap, new_mac_port_hashmap)

        # Save the extracted configuration to a file
        save_config_to_file(extracted_config, extracted_config_file)
        print(f"Extracted configuration saved to {extracted_config_file}")

    with open(extracted_config_file, "r") as file:
        config_text = file.read()
    # Replace port numbers in the extracted configuration
    updated_config_text = replace_port_numbers(config_text, old_mac_port_hashmap, new_mac_port_hashmap)

    # Now process the extracted_config.txt files
    output_folder = "OUTPUT"
    output_file = "NEW_9300_config.txt"
    extracted_config_file = "extracted_config.txt"

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.join(output_folder, output_file)
    with open(output_file_path, "w") as file:
        file.write(updated_config_text)
        print(f"Updated configuration saved to {output_file_path}")