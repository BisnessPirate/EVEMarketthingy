import numpy as np
import pandas as pd

import time
import market


def main_program(sell_station, sell_region, buy_region, min_sell,
                 min_per_day_sold, min_isk_volume, min_daily_profit, broker_fee,
                 transaction_tax, buy_from_buy_orders, sell_to_buy_orders,
                 sell_to_region, history_size, days_not_sold_per_month, esi_client, esi_app):
    """

    Function first pulls all item data from where you want to sell your items. Then it filters all items based on some
    criteria on the items you are interested in importing like minimum that get sold everyday. This is to reduce the
    amount of ESI calls that need to be made. Then it pulls all the items from the region where you want to buy your
    items and more filters get applied to get the final list of items.

    :param sell_station: integer station ID all the items will be sold to
    :param sell_region: integer region ID where you will sell the items
    :param buy_region: integer region ID where you will buy the items
    :param min_sell: integer minimum sell price to filter items you want to import
    :param min_per_day_sold: integer  minimum amount of times the items gets sold every day
    :param min_isk_volume: integer minimum ISK throughput for an item everyday
    :param min_daily_profit: integer minimum daily profit you would make on an item if you captured the whole market
    :param broker_fee: integer broker fee
    :param transaction_tax: integer transaction tax
    :param buy_from_buy_orders: boolean to decide if you buy from buy orders or sell orders
    :param sell_to_buy_orders: boolean to decide if you sell to buy order or put a sell order on the market
    :param sell_to_region: boolean to decide if you base prices of the region price or just the station you sell the item
    :param history_size: integer minimum amount of days there is data on the item where you're selling it
    :param days_not_sold_per_month: amount of days it the item hasn't sold any in the last month
    :param esi_client: ESI client
    :param esi_app: ESI app
    :return: returns a pandas dataframe with all items that are worthy to import.
    """

    start = time.time()  # This is to keep track of how long this function takes for improving speed purposes.

    total_tax = broker_fee + transaction_tax

    # Check if the orders need to be pulled from station or from a station.
    if sell_to_region == True:
        orders_sell_region = market.request_all_orders_region(sell_region, esi_client, esi_app)
    else:
        orders_sell_region = market.request_all_orders_station(sell_station, esi_client, esi_app)

    prices_sell = market.find_price(orders_sell_region, is_buy_order=sell_to_buy_orders)

    # checks how the items are going to be sold to apply the proper taxes
    if sell_to_buy_orders == True:
        prices_sell['price'] = prices_sell['price'] - prices_sell['price'] * transaction_tax
    else:
        prices_sell['price'] = prices_sell['price'] - prices_sell['price'] * total_tax

    # Sort based on the minimum sell price
    prices_sell = prices_sell[prices_sell['price'] >= min_sell]

    item_list = prices_sell.index.tolist()
    histories = market.get_histories(item_list, sell_region, esi_client, esi_app)

    all_volumes = market.volume_filter(histories=histories, prices=prices_sell, days_back=history_size,
                                       tolerance=days_not_sold_per_month)

    volumes_df = pd.DataFrame.from_dict(all_volumes, orient='index',
                                        columns=['price', 'volume_per_day', 'sold_ISK_volume'])

    # Filter based on amount sold per day and minimum amount ISK wise
    sold_filtered = volumes_df[volumes_df['volume_per_day'] >= min_per_day_sold]
    isk_filtered = sold_filtered[sold_filtered['sold_ISK_volume'] >= min_isk_volume]

    items_to_check = isk_filtered.index.tolist()

    # all the items from the region you're buying everything from.
    # There're some issues pulling them  from a specific station so only region specific for now.

    buy_items = market.get_from_region(items_to_check, buy_region, client=esi_client, app_esi=esi_app)

    cheapest_buy = market.find_price(buy_items, is_buy_order=buy_from_buy_orders)

    prices_buy_after_tax = pd.DataFrame()
    prices_buy_after_tax['volume_per_day'] = isk_filtered['volume_per_day']

    if buy_from_buy_orders == True:
        prices_buy_after_tax['price'] = cheapest_buy['price'] - cheapest_buy['price'] * broker_fee
    else:
        prices_buy_after_tax['price'] = cheapest_buy['price']

    # create the item profit dataframe
    item_profits = pd.DataFrame(columns=['profit per day', 'margin', 'volume_per_day', 'remaining', 'days_remaining'])

    item_profits['volume_per_day'] = prices_buy_after_tax['volume_per_day'].astype(int)
    item_profits['profit per day'] = (isk_filtered['price'] - prices_buy_after_tax['price']) * isk_filtered[
        'volume_per_day']
    item_profits['margin'] = (
                ((isk_filtered['price'] - prices_buy_after_tax['price']) / prices_buy_after_tax['price']) * 100)
    item_profits['remaining'] = market.get_left_on_market(orders=orders_sell_region, items=item_profits.index.tolist(),
                                                          is_buy_order=sell_to_buy_orders)

    item_profits['days_remaining'] = np.floor(item_profits['remaining'] / isk_filtered['volume_per_day'])

    items_left = item_profits[item_profits['profit per day'] >= min_daily_profit]

    sorted_items = items_left.sort_values(by='profit per day', ascending=False)

    item_list_sorted = sorted_items.index.tolist()

    item_data = market.get_item_data(item_list_sorted, client= esi_client, app_esi=esi_app)

    items_named = sorted_items
    items_named['size'] = item_data['packaged_volume']
    items_named['margin'] = items_named['margin'].astype(int)

    items_named = items_named.rename(dict(zip(item_list_sorted, item_data['name'])))
    items_named['profit per day'] = items_named['profit per day'].astype(int)

    end = time.time()
    print(end - start)
    return items_named
