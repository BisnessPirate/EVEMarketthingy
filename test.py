from esipy import EsiApp
from esipy import EsiClient
from esipy import EsiSecurity
from esipy.utils import generate_code_verifier

import pandas as pd

import market

app_info = pd.read_csv('appinfo.csv', index_col = 0)

first_time = app_info['key']['first_time']

# initialize all ESI stuff
esi_app_create = EsiApp()
app_esi = esi_app_create.get_latest_swagger

security_app = EsiSecurity(
    redirect_uri=app_info['key']['redirect_uri'],
    client_id=app_info['key']['client_id'],
    code_verifier=generate_code_verifier()
)

client = EsiClient(retry_requests=True, headers={'User-Agent': "Bisnesspirate's EVEMarket app"},
                   raw_body_only=False, security=security_app)

security_app.update_token({
    'access_token': '',
    'expires_in': -1,
    'refresh_token': app_info['key']['refresh_token']
})

scopes_limited = "esi-markets.structure_markets.v1"
scopes_list = scopes_limited.split()


orders, data = market.request_all_orders_station(1027847407700, client, app_esi)

print(data[0])

for key in data[0]:
    print(key)
    print(data[0][key])
