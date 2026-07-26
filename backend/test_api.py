import urllib.request, json

r = urllib.request.urlopen('http://localhost:8001/api/products?page_size=3')
d = json.loads(r.read())
print("total:", d['total'])
for i in d['items']:
    print(f"  {i['name']} | brand={i.get('brand')} | recommend={i.get('is_recommend')} | new={i.get('is_new')} | sale={i.get('is_sale')}")
    print(f"    image: {i['image'][:80]}")
