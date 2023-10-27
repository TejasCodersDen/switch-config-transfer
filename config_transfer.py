import os
import re

# Function to read MAC address and corresponding port information from a log file
def read_mac_port_hashmap(log_file_path):
    with open(log_file_path, 'r') as file:
        log_contents = file.read()

    # Use regular expressions to extract MAC address, entry type (STATIC or DYNAMIC), and port
    mac_port_entries = re.findall(r"(\w+\.\w+\.\w+)\s+(STATIC|DYNAMIC)\s+(\S+)", log_contents)

    # Create a dictionary (hashmap) where MAC addresses are keys and ports are values
    # Remove "Gi" and "Ti" prefixes from the port names, and exclude certain ports
    mac_port_hashmap = {mac: port.replace("Gi", "").replace("Ti", "") for mac, _, port in mac_port_entries
                        if port not in ["Vl1", "Po1", "CPU"]}

    return mac_port_hashmap

# Function to extract interface configurations from a config text using regular expressions
def extract_interfaces(config_text, old_mac_port_hashmap, new_mac_port_hashmap):
    # Define a regular expression pattern to match interface configurations
    interface_pattern = r'interface GigabitEthernet(\d+)/0/(\d+)(.*?)\!'
    matches = re.finditer(interface_pattern, config_text, re.DOTALL)

    extracted_config = {}

    # Iterate through the matched interface configurations
    for match in matches:
        interface_group = int(match.group(1))
        current_interface = f"GigabitEthernet{interface_group}/0/{match.group(2)}"
        interface_config = match.group(3).strip()

        # Check if the current interface is in the old MAC address to port hashmap
        for mac, port in old_mac_port_hashmap.items():
            if current_interface == f"GigabitEthernet{port}":
                # Check if the MAC address is in the new MAC address hashmap
                new_port = new_mac_port_hashmap.get(mac)
                if new_port is not None:
                    print(f"Found MAC address {mac} on port {port}. Replaced with port {new_port}.")
                    extracted_config[current_interface] = interface_config
                else:
                    print(f"Found MAC address {mac} on port {port}. MAC address not found in new MAC address file.")

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
    updated_config = config_text

    # Iterate through the old MAC address to port hashmap
    for old_mac, old_port in old_port_to_mac.items():
        new_port = new_port_to_mac.get(old_mac)
        if new_port:
            old_interface = f"GigabitEthernet{old_port}"
            new_interface = f"GigabitEthernet{new_port}"
            updated_config = updated_config.replace(old_interface, new_interface)
            print(f"Replaced {old_interface} with {new_interface}")

    return updated_config

if __name__ == "__main__":
    # List MAC_ADD and CONFIG files
    mac_add_files = [file for file in os.listdir("MAC_ADD") if "3850" in file]
    config_files = [file for file in os.listdir("CONFIG") if "3850" in file]

    for old_mac_add_file in mac_add_files:
        old_mac_port_hashmap = read_mac_port_hashmap(os.path.join("MAC_ADD", old_mac_add_file))

        # Search for the corresponding new MAC file in the MAC_ADD directory based on partial matching
        new_mac_add_file = next((file for file in os.listdir("MAC_ADD") if "9300" in file and file[:3] == old_mac_add_file[:3]), None)

        if new_mac_add_file:
            new_mac_port_hashmap = read_mac_port_hashmap(os.path.join("MAC_ADD", new_mac_add_file))

            for old_config_file in config_files:
                input_file = os.path.join("CONFIG", old_config_file)
                output_file_prefix = input_file.split(".")[0]
                output_file = f"{output_file_prefix}_NEW.log"

                with open(input_file, "r") as file:
                    config_text = file.read()
                    print(f"Reading configuration from {input_file}")

                extracted_config = extract_interfaces(config_text, old_mac_port_hashmap, new_mac_port_hashmap)
                save_config_to_file(extracted_config, "extracted_config.txt")
                print(f"Extracted configuration saved to extracted_config.txt")

                with open("extracted_config.txt", "r") as file:
                    config_text = file.read()

                updated_config_text = replace_port_numbers(config_text, old_mac_port_hashmap, new_mac_port_hashmap)

                with open(output_file, "w") as file:
                    file.write(updated_config_text)
                    print(f"Updated configuration saved to {output_file}")

        else:
            print(f"New MAC file not found for {old_mac_add_file}")