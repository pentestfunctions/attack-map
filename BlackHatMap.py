# The abuseipdb database contains the known IPs associated with abuse. Currently assigned to all historical ABUSE ips, one IP per line
# The dbip-city file is structure as the range it is on in the first 2 columns such as:
# 192.42.96.0,192.42.96.255,NA,US,California,"Los Angeles (Westlake)",34.0507,-118.277
# Using this we calculate the range the IP fits in and assign its GPS coordinates to the map
# After that we can load our chosen csv/database file and for each line that has an IP address we check to see if it matches an abuse IP
# IF it has an abuse IP, we then check its gps coordinates and then add all the info as a marker using folium to the map

import os
import re
import ipaddress
import folium
from folium import IFrame
from intervaltree import IntervalTree

class IPAnalyzer:
    def __init__(self, database_file, abuse_file, dbip_file):
        self.database_file = database_file
        self.abuse_file = abuse_file
        self.dbip_file = dbip_file

    def normalize_data(self):
        with open(self.database_file, 'r') as file:
            lines = file.readlines()
    
        with open(self.database_file, 'w') as file:
            for line in lines:
                # Removing unwanted characters including brackets and replacing commas with spaces
                line = re.sub(r"[`'\"\[\](){}]", " ", line)  # Regex pattern to help normalize SQL style format
                line = line.replace(',', ' ')  # Replacing commas with spaces
                file.write(line)

    def read_ip_ranges(self):
        ip_ranges = IntervalTree()
        with open(self.dbip_file, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                start_ip_int = int(ipaddress.ip_address(parts[0]))
                end_ip_int = int(ipaddress.ip_address(parts[1])) + 1
                lat, lon = parts[-2], parts[-1]
                data = {'city': ','.join(parts[4:-2]), 'lat': lat, 'lon': lon}
                if start_ip_int < end_ip_int:
                    ip_ranges[start_ip_int:end_ip_int] = data
        # Debug: Print a few ranges for verification
        for interval in list(ip_ranges)[:5]:
            print(interval)
        return ip_ranges

    def is_ip_in_range(self, ip_obj, ip_ranges):
        ip_int = int(ip_obj)
        results = ip_ranges[ip_int]
        if results:
            # Find the interval where the IP is closest to the start of the range
            closest_interval = min(results, key=lambda interval: ip_int - interval.begin)
            return closest_interval.data
        return None

    def find_and_match_ips(self):
        self.normalize_data()
    
        # Load abuse IP data
        with open(self.abuse_file, 'r') as file:
            abuse_ips = {line.strip() for line in file}
    
        # Prepare IP range mapping
        ip_ranges = self.read_ip_ranges()
    
        # Compile regex pattern
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
        # Search for IPs in database
        matched_data = []
        with open(self.database_file, 'r') as file:
            for line in file:
                found_ips = ip_pattern.findall(line)
                for ip in found_ips:
                    if ip in abuse_ips:
                        ip_obj = ipaddress.ip_address(ip)
                        data = self.is_ip_in_range(ip_obj, ip_ranges)
                        if data and data['lat'] != '0.0' and data['lon'] != '0.0':
                            matched_data.append({'ip': ip, 'city': data['city'], 'lat': data['lat'], 'lon': data['lon'], 'content': line.strip()})
        
        return matched_data

    def create_map(self, matched_data, map_file='ip_map.html'):
        map = folium.Map(location=[0, 0], zoom_start=2)
        for data in matched_data:
            try:
                lat = float(data['lat'])
                lon = float(data['lon'])
                # Debug: Print latitude and longitude
                print(f"Adding marker for IP {data['ip']} at {lat}, {lon}")
            except ValueError:
                print(f"Invalid coordinates for IP {data['ip']}: {data['lat']}, {data['lon']}")
                continue  # Skip invalid coordinates

            html_content = f"<b>IP:</b> {data['ip']}<br><b>City:</b> {data['city']}<br><b>Details:</b><br>{' '.join(data['content'].split())}"
            iframe = IFrame(html_content, width=300, height=200)
            popup = folium.Popup(iframe, max_width=500)
            folium.Marker([lat, lon], popup=popup, icon=folium.Icon(color='blue')).add_to(map)

        map.save(map_file)

# Main execution
ip_analyzer = IPAnalyzer('CardingMafia.csv', 'abuseipdb-s100-all.ipv4', 'dbip-city-lite-2023-12.csv')
matched_ips = ip_analyzer.find_and_match_ips()
ip_analyzer.create_map(matched_ips)
