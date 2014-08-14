import csv
import re
import requests
import json

def is_valid_url(url):
    return re.match(r'https?://', url, re.I) is not None

def main():
    reader = csv.reader(open('open_data_data_inventory_audit.csv', 'r'))
    for (i, line) in enumerate(reader):
        if i==0:
            continue

        data_json_url = line[5]
        if is_valid_url(data_json_url):
            r = requests.get(data_json_url)
            decoded_json = None
            try:
                decoded_json = json.loads(r.content)
            except:
                print 'HTTP %d: %s' % (r.status_code, data_json_url)





if __name__ == '__main__':
    main()