# OurAirports (public domain): airports with scheduled flights and an IATA code
import csv, json, re
out=[]
for r in csv.DictReader(open('/tmp/ap/airports.csv',encoding='utf-8')):
    if r['scheduled_service']!='yes' or not r['iata_code'] or r['type'] not in ('large_airport','medium_airport','small_airport'): continue
    if not re.fullmatch(r'[A-Z]{3}',r['iata_code']): continue
    ru=[k.strip() for k in r['keywords'].split(',') if re.search('[а-яА-ЯёЁ]',k)]
    out.append([r['iata_code'],r['name'],r['municipality'] or '',round(float(r['latitude_deg']),3),round(float(r['longitude_deg']),3),' '.join(ru)[:80],1 if r['type']=='large_airport' else 0])
json.dump(out,open('site/data/airports.json','w'),ensure_ascii=False,separators=(',',':'))
print(len(out), sum(1 for o in out if o[5]))
