import numpy as np
import pandas as pd

import datetime


def request_all_orders_station(station_id, client, app_esi):
    """

    :param station_id: int station ID
    :param client:an esi_client to get the orders
    :param app_esi: an esi app
    :return: dataframe with all the market orders
    """

    try:
        station_id_temp = int(station_id)
    except:
        raise TypeError(station_id + ' is not an integer')
    all_orders = pd.DataFrame()
    requests_data = list()

    get_orders_temp = app_esi.op['get_markets_structures_structure_id'](structure_id=station_id_temp, page=1)
    res = client.head(get_orders_temp)

    operations = list()

    if res.status == 200:  # Checks if we successfully got the header.
        number_of_pages = res.header['X-pages'][0]

        for page in range(1, number_of_pages + 1):
            operations.append(
                app_esi.op['get_markets_structures_structure_id'](structure_id=station_id_temp, page=page))

    else:
        raise Exception("could not find anything" + res)

    results = client.multi_request(operations)

    for request in results:
        requests_data.extend(list(request[1].data))

    all_orders = pd.DataFrame.from_records(requests_data)

    return all_orders


def request_all_orders_region(region_id, client, app_esi):
    """
    :param region_id: region ID
    :param client: an esi
    :param app_esi: an esi app
    :return:
    """

    try:
        region_id_temp = int(region_id)
    except:
        raise TypeError(str(region_id) + ' is not an integer')

    requests_data = list()

    get_orders_temp = app_esi.op['get_markets_region_id_orders'](region_id=region_id_temp, page=1)
    res = client.head(get_orders_temp)

    operations = list()

    if res.status == 200:  # Checks if we sucesfully got the header.
        number_of_pages = res.header['X-pages'][0]

        for page in range(1, number_of_pages + 1):
            operations.append(app_esi.op['get_markets_region_id_orders'](region_id=region_id_temp, page=page))

    else:
        raise Exception("could not find anything")

    results = client.multi_request(operations)

    for request in results:
        requests_data.extend(list(request[1].data))

    all_orders = pd.DataFrame.from_records(requests_data)

    return all_orders


def find_price(orders, is_buy_order=False):
    """
    :param orders:  pandas dataframe with columns: 'type_id', 'is_buy_order', 'price'
    :param is_buy_order: boolean
    :return: dataframe with all the prices
    """
    if type(is_buy_order) is not bool:
        raise TypeError('is_buy_order has to be a boolean')

    unique_orders = orders['type_id'].unique()

    price_dict = dict()

    for type_id in unique_orders:
        current_items = orders
        current_items = current_items[current_items['is_buy_order'] == is_buy_order]
        current_items = current_items[current_items['type_id'] == type_id]

        if is_buy_order == True:
            price = current_items['price'].max()
        else:
            price = current_items['price'].min()

        price_dict[str(type_id)] = [price]

    return pd.DataFrame.from_dict(price_dict, orient='index', columns=['price'])


def get_histories(items, region_id, client, app_esi):
    """

    :param items: item IDs you want to cehck
    :param region_id: region ID
    :param client: esi client
    :param app_esi: esi app
    :return: dictionary with the histories
    """

    histories = list()

    operations = list()

    counter = 0
    for item_id in items:

        try:
            item_id = int(item_id)
        except TypeError:
            raise TypeError(f'item {counter} can not be converted to an integer')

        operations.append(app_esi.op['get_markets_region_id_history'](region_id=region_id, type_id=item_id))

        counter += 1

    results = client.multi_request(operations)

    for request in results:
        history_frame_temp = pd.DataFrame.from_records(list(request[1].data))
        # print(history_frame_temp)
        histories.append(history_frame_temp)

    return dict(zip(items, histories))


def get_from_region(items, region_id, client, app_esi):
    """

    :param items: all item IDs you want to check
    :param region_id: region ID
    :param client: esi client
    :param app_esi:  esi app
    :return: dataframe with all the orders
    """

    count = 0

    item_list = list()

    operations = list()

    for item in items:

        try:
            item_id = int(item)
        except TypeError:
            raise TypeError(f'item {count} could not be interpreted as type ID')

        operations.append(app_esi.op['get_markets_region_id_orders'](region_id=region_id, type_id=item_id))
        count += 1

    results = client.multi_request(operations)

    for request in results:
        item_list.extend(list(request[1].data))

    return pd.DataFrame.from_records(item_list)


def get_item_data(items, client, app_esi):
    """
    :param items: all the item IDs you want to check
    :param client: esi CLIENT
    :param app_esi:
    :return: returns a data frame with all the item names
    """
    count = 0
    list_item_data = list()

    operations = list()

    for item in items:
        try:
            item_id = int(item)
        except TypeError:
            raise TypeError(f'item {count} could not be interpreted as type ID')

        operations.append(app_esi.op['get_universe_types_type_id'](type_id=item_id))
        count += 1

    results = client.multi_request(operations)

    for request in results:
        list_item_data.append(request[1].data)

    frame = pd.DataFrame.from_records(list_item_data)  # .set_index('type_id')
    frame['type_id'] = frame['type_id'].astype(str)
    return frame.set_index('type_id')


def volume_filter(histories, prices, days_back, tolerance):
    """
    filters the histories of the items given based on how much of them gets sold in a given period.
    :param histories: histories of all the items you're checking
    :param prices: dataframe with all the items and their price
    :param days_back: amount of days you look into the past
    :param tolerance: how many days in the period you look into are allowed to have no data.
    :return: returns a new dataframe that's filtered
    """

    # Can probably do this more efficiently by using pandas shit

    seconds_day = datetime.timedelta(days=1).total_seconds()
    all_volumes = dict()

    today = datetime.date.today()
    time_delta_history = datetime.timedelta(days=days_back + tolerance).total_seconds()

    for key in histories:
        if len(histories[key]) > days_back:
            date_delta = np.abs(histories[key].loc[len(histories[key]) - days_back]['date'].v - today)
            date_seconds_delta = date_delta.total_seconds()

            if time_delta_history >= date_seconds_delta:
                item_price_temp = prices.loc[key]['price']
                # work on picking the correct number for this
                sold_mean_temp = histories[key].tail(days_back)['volume'].sum() / (date_seconds_delta / seconds_day)
                all_volumes[key] = [item_price_temp, sold_mean_temp, item_price_temp * sold_mean_temp]

    return all_volumes


def get_left_on_market(orders, items, is_buy_order):
    """
    find out how many of an item is left on the market, either for buy orders or for sell orders.

    :param orders:  dataframe with all the orders you're sifting through
    :param items: item IDs of all the items you want to check
    :param is_buy_order:  boolean
    :return: dataframe with what is left on the market
    """
    left_on_market = dict()

    for item in items:
        try:
            item_id = int(item)
        except:
            raise TypeError(f'item {count} could not be interpreted as an int of a type ID')

        new_orders = orders[orders['type_id'] == item_id]
        new_orders = new_orders[new_orders['is_buy_order'] == is_buy_order]

        volume_left = new_orders['volume_remain'].sum()

        left_on_market[str(item_id)] = volume_left

    left_on_market = pd.Series(left_on_market)
    return left_on_market
