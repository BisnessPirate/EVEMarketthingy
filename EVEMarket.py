from esipy import EsiApp
from esipy import EsiClient
from esipy import EsiSecurity

import numpy as np
import pandas as pd

from PySide2.QtWidgets import (QPushButton,
                               QPlainTextEdit, QComboBox, QTextBrowser, QTableView)

from PySide2.QtUiTools import QUiLoader
#from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2.QtCore import QFile
from PySide2 import QtCore

import time
import sys
import datetime

"""
From https://stackoverflow.com/questions/44603119/how-to-display-a-pandas-data-frame-with-pyqt5
Changed the sort function to if it is sorted to inverse it.
Also made it compatible with Pyside2
"""

class PandasModel(QtCore.QAbstractTableModel): 
    def __init__(self, df = pd.DataFrame(), parent=None): 
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        self._df = df

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except (IndexError, ):
                return None
        elif orientation == QtCore.Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self._df.index.tolist()[section]
            except (IndexError, ):
                return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None

        if not index.isValid():
            return None

        return str(self._df.iloc[index.row(), index.column()])

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self._df.columns[index.column()]
        if hasattr(value, 'toPyObject'):
            # PyQt4 gets a QVariant
            value = value
        else:
            # PySide gets an unicode
            dtype = self._df[col].dtype
            if dtype != object:
                value = None if value == '' else dtype.type(value)
        self._df.set_value(row, col, value)
        return True

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self._df.index)

    def columnCount(self, parent=QtCore.QModelIndex()): 
        return len(self._df.columns)

    def sort(self, column, order):
        colname = self._df.columns.tolist()[column]
        
        temp_df = self._df[colname]
        
        if temp_df.is_monotonic_decreasing == True:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending = False == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()
            
        elif temp_df.is_monotonic_increasing == True:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending = True == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()
        else:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending = order == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()

def request_all_orders_station(station_id):
    """
    This function gets all orders from the station with the given station_d
    """
    
    
    try:
        station_id_temp = int(station_id)
    except:
        raise TypeError(station_id + ' is not an integer')

    all_orders = pd.DataFrame()
    page_number = 1

    data_list = list()

    while True:
        get_orders_temp = app_esi.op['get_markets_structures_structure_id'](structure_id = station_id_temp, page = page_number)
        response_temp = client.request(get_orders_temp)

      
        data_list.extend(list(response_temp.data))

        if len(response_temp.data) == 0:
            #print(str(page_number-1) + " pages total")
            break
        else:
            page_number += 1
            
    all_orders = pd.DataFrame.from_records(data_list)       

    return all_orders
        
        
def request_all_orders_region(region_id):
    
    try:
        region_id_temp = int(region_id)
    except:
        raise TypeError(str(station) + ' is not an integer')

    all_orders = pd.DataFrame()
    page_number = 1

    data_list = list()

    while True:
        get_orders_temp = app_esi.op['get_markets_region_id_orders'](region_id = region_id_temp, page = page_number)
        response_temp = client.request(get_orders_temp)
        data_list.extend(list(response_temp.data))
        if len(response_temp.data) == 0:
            #print(str(page_number-1) + " pages total")
            break
        else:
            page_number += 1
    all_orders = pd.DataFrame.from_records(data_list)       

    return all_orders

        
def find_price(orders, is_buy_order = False):
    """
    orders is a pandas dataframe with columns: 'type_id', 'is_buy_order', 'price' 
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

    return pd.DataFrame.from_dict(price_dict, orient = 'index', columns = ['price'])

def get_histories(items, region_id):
    
    histories = dict()
    
    counter = 0
    for item_id in items:
        
        try:
            item_id = int(item_id)
        except:
            raise TypeError(f'item {counter} can not be converted to an integer')
        
        history_frame_temp = pd.DataFrame()
        
        get_history_temp = app_esi.op['get_markets_region_id_history'](region_id = region_id, type_id = item_id)
        response_history_temp = client.request(get_history_temp)
        
        history_frame_temp = pd.DataFrame.from_records(list(response_history_temp.data))
        histories[str(item_id)] = history_frame_temp
        counter += 1
        
    return histories


def get_from_region(items, region_id):
    count = 0
    item_list = list()
    for item in items:
        
        try:
            item_id = int(item)
        except:
            raise TypeError(f'item {count} could not be interpreted as type ID')
        
        get_item_temp = app_esi.op['get_markets_region_id_orders'](region_id = region_id, type_id = item_id)
        response_temp =  client.request(get_item_temp)
        
        item_list.extend(list(response_temp.data))

    
        count += 1
    
    return pd.DataFrame.from_records(item_list)

    
def get_item_data(items):
    count = 0
    list_item_data = list()
    for item in items:
        try:
            item_id = int(item)
        except:
            raise TypeError(f'item {count} could not be interpreted as type ID')
        
        get_item_temp = app_esi.op['get_universe_types_type_id'](type_id = item_id)
        response_temp =  client.request(get_item_temp)
        list_item_data.append(response_temp.data)
        count += 1   
        
    frame = pd.DataFrame.from_records(list_item_data)#.set_index('type_id')
    frame['type_id'] = frame['type_id'].astype(str)
    return frame.set_index('type_id')
    
def volume_filter(histories, prices, days_back, tolerance):
    
    seconds_day = datetime.timedelta(days = 1).total_seconds()
    all_volumes = dict()
    
    today = datetime.date.today()
    time_delta_history = datetime.timedelta(days = days_back + tolerance).total_seconds()

    for key in histories:
        if len(histories[key]) > days_back:
            date_delta = np.abs(histories[key].loc[len(histories[key]) - days_back]['date'].v - today)
            date_seconds_delta = date_delta.total_seconds()
            
            if time_delta_history >= date_seconds_delta:
                
                item_price_temp = prices.loc[key]['price']
                #work on picking the correct number for this
                sold_mean_temp = histories[key].tail(days_back)['volume'].sum() / (date_seconds_delta / seconds_day)
                all_volumes[key] = [item_price_temp, sold_mean_temp, item_price_temp*sold_mean_temp]
    
    return all_volumes

def get_left_on_market(orders, items, is_buy_order):
    left_on_market = dict()
    
    for item in items:
        try:
            item_id = int(item)
        except:
            raise TypeError(f'item {count} could not be interpreted as an int of a type ID')
        
        new_orders = orders[orders['type_id'] ==  item_id]
        new_orders = new_orders[new_orders['is_buy_order'] == is_buy_order]
        
        volume_left = new_orders['volume_remain'].sum()
        
        left_on_market[str(item_id)] = volume_left
        
        
        
    left_on_market = pd.Series(left_on_market)
    return left_on_market

#Run this, wait a bit and enjoy the data
def main_program(sell_station, buy_station, sell_region, buy_region, min_sell,
                 min_per_day_sold, min_ISK_volume, min_daily_profit, broker_fee,
                 transaction_tax, buy_from_buy_orders, sell_to_buy_orders, 
                 sell_to_region, history_size, days_not_sold_per_month):
    
    start = time.time()
    total_tax = broker_fee + transaction_tax

    time_delta_history = datetime.timedelta(days = history_size + days_not_sold_per_month).total_seconds()

    if sell_to_region == True:
        orders_sell_region = request_all_orders_region(sell_station)
    else:
        orders_sell_region = request_all_orders_station(sell_station)

    prices_sell = find_price(orders_sell_region, is_buy_order = sell_to_buy_orders)


    if sell_to_buy_orders == True:
        prices_sell['price'] = prices_sell['price'] - prices_sell['price'] * transaction_tax
    else:
        prices_sell['price'] = prices_sell['price'] - prices_sell['price'] * total_tax


    prices_sell = prices_sell[prices_sell['price'] >= min_sell]

    item_list = prices_sell.index.tolist()
    histories = get_histories(item_list, sell_region)


    all_volumes = volume_filter(histories=histories, prices=prices_sell, days_back= history_size, tolerance= days_not_sold_per_month)


    volumes_df = pd.DataFrame.from_dict(all_volumes, orient='index', columns=['price','volume_per_day', 'sold_ISK_volume'])

    sold_filtered = volumes_df[volumes_df['volume_per_day'] >= min_per_day_sold] 
    ISK_filtered = sold_filtered[sold_filtered['sold_ISK_volume'] >= min_ISK_volume]

    items_to_check = ISK_filtered.index.tolist()


    buy_items = get_from_region(items_to_check, buy_region)

    cheapest_buy = find_price(buy_items, is_buy_order = buy_from_buy_orders)

    prices_buy_after_tax = pd.DataFrame()
    prices_buy_after_tax['volume_per_day'] = ISK_filtered['volume_per_day']

    if buy_from_buy_orders == True:
        prices_buy_after_tax['price'] = cheapest_buy['price'] - cheapest_buy['price'] * broker_fee
    else:
        prices_buy_after_tax['price'] = cheapest_buy['price']

    item_profits = pd.DataFrame(columns = ['profit', 'margin', 'volume_per_day' ,'remaining', 'days_remaining'])

    item_profits['volume_per_day'] = prices_buy_after_tax['volume_per_day'].astype(int)
    item_profits['profit'] = (ISK_filtered['price'] - prices_buy_after_tax['price']) * ISK_filtered['volume_per_day']
    item_profits['margin'] = (((ISK_filtered['price'] - prices_buy_after_tax['price']) / prices_buy_after_tax['price']) * 100).astype(int)
    item_profits['remaining'] = get_left_on_market(orders=orders_sell_region,items=item_profits.index.tolist(),is_buy_order=sell_to_buy_orders)

    item_profits['days_remaining'] = np.floor(item_profits['remaining'] / ISK_filtered['volume_per_day'])



    items_left = item_profits[item_profits['profit'] >= min_daily_profit]

    sorted_items = items_left.sort_values(by = 'profit', ascending = False)



    item_list_sorted = sorted_items.index.tolist()


    item_data = get_item_data(item_list_sorted)

    items_named = sorted_items
    items_named['size'] = item_data['packaged_volume']

    items_named = items_named.rename(dict(zip(item_list_sorted,item_data['name'])))
    items_named['profit'] = items_named['profit'].astype(int)

    end = time.time()
    #print(end - start)
    return items_named

class Form(QtCore.QObject):
    
    
    def __init__(self, ui_file, parent = None):
        super(Form, self).__init__(parent)
        #QtWidgets.QMainWindow.__init__(self)
        #Ui_MainWindow.__init__(self)
        
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)
 
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        
        self.showText = self.window.findChild(QPushButton, 'showText')
        self.loginButton = self.window.findChild(QPushButton, 'loginButton')
        self.updateToken = self.window.findChild(QPushButton, 'updateToken')
        
        
        
        #self.testButton = self.window.findChild(QPushButton, 'testButton')
        
        
        
        
        
        self.redirect = self.window.findChild(QPlainTextEdit, 'redirect')
        self.clientID = self.window.findChild(QPlainTextEdit, 'clientID')
        self.secretKey = self.window.findChild(QPlainTextEdit, 'secretKey')
        self.refreshToken = self.window.findChild(QPlainTextEdit, 'refreshToken')
        
        self.brokerFee = self.window.findChild(QPlainTextEdit, 'brokerFee')
        self.transactionTax = self.window.findChild(QPlainTextEdit, 'transactionTax')
        
        self.buyStationID = self.window.findChild(QPlainTextEdit, 'buyStationID')
        self.sellStationID = self.window.findChild(QPlainTextEdit, 'sellStationID')
        self.buyRegionID = self.window.findChild(QPlainTextEdit, 'buyRegionID')
        self.sellRegionID = self.window.findChild(QPlainTextEdit, 'sellRegionID')
        
        self.minSellPrice = self.window.findChild(QPlainTextEdit, 'minSellPrice')
        self.historySize = self.window.findChild(QPlainTextEdit, 'historySize')
        self.minDailyProfit = self.window.findChild(QPlainTextEdit, 'minDailyProfit')
        self.minISKVolume = self.window.findChild(QPlainTextEdit, 'minISKVolume')
        self.minDaySold = self.window.findChild(QPlainTextEdit, 'minDaySold')
        self.daysNotSold = self.window.findChild(QPlainTextEdit, 'daysNotSold')
        
        self.refreshURL = self.window.findChild(QPlainTextEdit, 'refreshURL')
        
        self.buyBuyOrders = self.window.findChild(QComboBox, 'buyBuyOrders')
        self.sellBuyOrders = self.window.findChild(QComboBox, 'sellBuyOrders')
        self.sellToRegion = self.window.findChild(QComboBox, 'sellToRegion')
        
        self.waitBox = self.window.findChild(QTextBrowser, 'waitBox')
        self.loginURL = self.window.findChild(QTextBrowser, 'loginURL')
        
        self.tableTest = self.window.findChild(QTableView, 'tableTest')
        
        

        
        
        self.showText.clicked.connect(self.show_text)
        self.loginButton.clicked.connect(self.login)
        self.updateToken.clicked.connect(self.refresh_refresh)
        
        self.redirect.setPlainText(app_info['key']['redirect_uri'])
        self.clientID.setPlainText(app_info['key']['client_id'])
        self.secretKey.setPlainText(app_info['key']['secret_key'])
        self.refreshToken.setPlainText(app_info['key']['refresh_token'])
        
        #url = 'https://www.google.com/'
        
        #self.webTest.load(QtCore.QUrl(url))
        #self.testButton.clicked.connect(self.print_url)
        
    def print_url(self):
        print(self.webTest.url().toString())
        
        
    def show_text(self):
        
        self.waitBox.setText("please wait")
        
        
        new_items = main_program(sell_station = int(self.sellStationID.toPlainText()),
                                 buy_station = int(self.sellStationID.toPlainText()),
                                 sell_region = int(self.sellRegionID.toPlainText()),
                                 buy_region = int(self.buyRegionID.toPlainText()),
                                 min_sell = float(self.minSellPrice.toPlainText()),
                                 min_per_day_sold = float(self.minDaySold.toPlainText()),
                                 min_ISK_volume = float(self.minISKVolume.toPlainText()),
                                 min_daily_profit = float(self.minDailyProfit.toPlainText()),
                                 broker_fee = float(self.brokerFee.toPlainText()),
                                 transaction_tax = float(self.transactionTax.toPlainText()),
                                 buy_from_buy_orders = bool(self.buyBuyOrders.currentText() == "True"),
                                 sell_to_buy_orders = bool(self.sellBuyOrders.currentText() == "True"), 
                                 sell_to_region = bool(self.sellToRegion.currentText() == "True"),
                                 history_size = int(self.historySize.toPlainText()),
                                 days_not_sold_per_month = int(self.daysNotSold.toPlainText()))
        
        self.test_model = PandasModel(new_items)
        self.tableTest.setModel(self.test_model)
        self.tableTest.horizontalHeader().sectionClicked.connect(self.sort_model)
        
        self.waitBox.setText("done")
        #print(new_items)
        
    def sort_model(self, column):
        self.waitBox.setText("please wait")
        self.test_model.sort(column,True)
        self.waitBox.setText("done")
        
    def login(self):
        
        global esi_app
        global app_esi
        global security_app
        global client
        
        esi_app = EsiApp()
        
        app_esi = esi_app.get_latest_swagger
        
        red_uri = self.redirect.toPlainText()
        cl_id = self.clientID.toPlainText()
        sec_key = self.secretKey.toPlainText()

        security_app = EsiSecurity(
            redirect_uri=red_uri,
            client_id=cl_id,
            secret_key=sec_key
        )
        
        app_info['key']['redirect_uri'] = red_uri
        app_info['key']['client_id'] = cl_id
        app_info['key']['secret_key'] = sec_key

        client = EsiClient(retry_requests = True, headers = {'User-Agent': "Bisness, Citadel test app"}, raw_body_only = False, security=security_app)
        
        url = security_app.get_auth_uri(state='SomeRandomGeneratedState', scopes=scopes_list)
        
        self.loginURL.setText(url)      
        
        
        
        
    
    def refresh_refresh(self):
        global security_app
        
        get_url = self.refreshURL.toPlainText()
        
        refresh_1st_part = get_url.split('/')[-1]
        refresh_token_2nd_part = refresh_1st_part.split('&')[0]
        refresh_token_3rd_part = refresh_token_2nd_part.split('?code=')[-1]
        
        tokens = security_app.auth(refresh_token_3rd_part)
        
        refresh_token = tokens['refresh_token']
        #print(refresh_token)
        #refresh_token = refresh_token_2nd_part
        
        
        security_app.update_token({
        'access_token' : '',
        'expires_in' : -1,
        'refresh_token' : refresh_token
        })
        
        self.refreshToken.setPlainText(refresh_token)
        
        app_info['key']['refresh_token'] = refresh_token
        
        app_info.to_csv('appinfo.csv')

main_window = "EVE_test.ui"

if __name__ == "__main__":
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance() 
        
    app_info = pd.read_csv('appinfo.csv', index_col = 0)
    
    first_time = app_info['key']['first_time']
    
    
    
    esi_app = EsiApp()
    app_esi = esi_app.get_latest_swagger
    
    security_app = EsiSecurity(
        redirect_uri =  app_info['key']['redirect_uri'],
        client_id = app_info['key']['client_id'],
        secret_key = app_info['key']['secret_key']
    )
    
    client = EsiClient(retry_requests = True, headers = {'User-Agent': "Bisness, Citadel test app"}, raw_body_only = False, security=security_app)
    
    security_app.update_token({
    'access_token' : '',
    'expires_in' : -1,
    'refresh_token' : app_info['key']['refresh_token']
    })
    
    scopes_limited = "esi-markets.structure_markets.v1"
    scopes_list = scopes_limited.split()
    
    window = Form(main_window)
    window.window.show()
    
    sys.exit(app.exec_())