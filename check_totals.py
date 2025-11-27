# Basit kontrol - her varlığın maliyetini göster
import pandas as pd
from io import StringIO

csv = """Kod,Adet,Maliyet
MEGMT,119.00,30.26
UUUU,10.92,21.59
Gram Altın,2.46,5666.50
YHB,36072.00,1.32
GGK,1365.00,4.94
URA,1350.00,1.67
OTJ,241.00,5.19
RUT,684.00,1.83
TKFEN,35.00,84.53
TRMET,41.00,85.23
Gram Gümüş,2672.84,63.93
GRID,0.45,155.57
ACLS,1.52,84.94
GFS,3.68,35.57
NB,11.00,9.94
CRDO,0.81,143.96
CEG,0.32,362.00
OSCR,5.42,21.57
META,0.39,596.97
AMZN,1.03,225.80
TSLA,0.57,405.98
MSFT,0.49,474.26
USD,703.50,42.22"""

df = pd.read_csv(StringIO(csv))

usd_try = 42.43
total = 0

for _, row in df.iterrows():
    kod = row['Kod']
    adet = float(row['Adet'])
    maliyet = float(row['Maliyet'])
    
    # ABD hisseleri USD, diğerleri TRY
    if kod in ['UUUU','GRID','ACLS','GFS','NB','CRDO','CEG','OSCR','META','AMZN','TSLA','MSFT']:
        maliyet_try = adet * maliyet * usd_try
    elif kod == 'USD':
        maliyet_try = adet * maliyet  # Zaten TRY
    else:
        maliyet_try = adet * maliyet
    
    total += maliyet_try
    print(f"{kod:15s} | {adet:10,.2f} adet × {maliyet:10,.2f} = ₺{maliyet_try:12,.2f}")

print(f"\n{'TOPLAM':15s} | {'':10s}   {'':10s}   ₺{total:12,.2f}")
print(f"\nBeklenen: ₺366,590")
print(f"Fark: ₺{total - 366590:,.2f}")
