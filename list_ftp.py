import urllib.request
import re
try:
    html = urllib.request.urlopen('https://ftp.ncbi.nlm.nih.gov/pathogen/Results/Salmonella/latest_kmer/Metadata/').read().decode()
    for match in re.findall(r'href=\"([^\"]+)\"', html):
        print(match)
except Exception as e:
    print('Error:', e)
