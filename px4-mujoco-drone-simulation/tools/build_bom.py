"""Reproduce EUR budget from recorded price quotes, not live guessed values."""
import csv,json
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RATE=Decimal('1.1204')
DATE='2026-10-05'
FX='https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html'
rows=[
    dict(component='Holybro X500 V2 PX4 development kit, Pixhawk 6C / M10',quantity=1,source_price='609.00',source_currency='USD',source='https://holybro.com/products/px4-development-kit-x500-v2',tax='checkout taxes/import charges excluded',status='listed_manufacturer_offer'),
    dict(component='ALLXF D-80Pro 40x-4K spherical gimbal camera',quantity=1,source_price='860.00',source_currency='USD',source='https://allxf.com/product/d-80pro-40x-4k-spherical-gimbal-camera/',tax='checkout taxes/import charges excluded; GCU inclusion unresolved',status='listed_manufacturer_offer'),
    dict(component='Khadas Edge2 Basic Maker Kit KEG2-B-001',quantity=1,source_price='239.95',source_currency='EUR',source='https://www.soundimports.eu/en/khadas-keg2-b-001.html',tax='retailer VAT included',status='listed_exact_variant_retailer_offer'),
    dict(component='XIAO ESP32S3 with SX1262 module',quantity=1,source_price='9.00',source_currency='EUR',source=None,tax='not specified',status='approximate_user_supplied_price'),
    dict(component='Lumenier NAV 12000mAh 4S 21700 Amprius XT60',quantity=1,source_price='218.99',source_currency='USD',source='https://www.lumenier.com/products/lumenier-nav-12000mah-4s-21700-amprius-lithium-ion-battery-xt60',tax='checkout taxes/import charges excluded',status='listed_manufacturer_offer_out_of_stock'),
]
def main():
    total=Decimal(0)
    for row in rows:
        value=Decimal(row['source_price'])/(RATE if row['source_currency']=='USD' else Decimal(1))
        total+=value*row['quantity'];row['unit_eur']=str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP));row['checked_on']=DATE
    out=dict(items=rows,eur_subtotal=str(total.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),date=DATE,usd_per_eur=str(RATE),exchange_source=FX,
             basis='mixed_tax_reference_parts_subtotal_not_delivered_or_complete_build_cost',
             kit_includes=['frame','Pixhawk6C','PM02V3','M10GPS','SiKtelemetry','4 KV920 motors','4 ESCs','PDB','6 propellers (4 installed,2 spares)','retainers'],
             exclusions=['shipping','import taxes/duties and conversion fees where not already included','custom mounts and wiring','charger','unknown GCU supply/inclusion','CAD PM06 versus included kit PM02 difference'])
    (ROOT/'docs/parts.json').write_text(json.dumps(out,indent=2))
    with (ROOT/'docs/parts.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('EUR subtotal',out['eur_subtotal'])
if __name__=='__main__':main()
