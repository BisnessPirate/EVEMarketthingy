from esipy import EsiApp
from esipy import EsiClient
from esipy import EsiSecurity
from esipy.utils import generate_code_verifier

from PySide2.QtWidgets import (QPushButton, QPlainTextEdit, QComboBox, QTextBrowser, QTableView, QLineEdit)

from PySide2.QtUiTools import QUiLoader

from PySide2.QtCore import QFile
from PySide2 import QtCore


import pandastable
import calculation
import compression

import sys
import traceback

import pandas as pd
import numpy as np
import re

import market


class Worker(QtCore.QRunnable):
    '''
    worker class for multithreading with Pyside2
    '''

    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.function = function

    def run(self):
        try:
            result = self.function(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing

        finally:
            self.signals.finished.emit()  # Done


class WorkerSignals(QtCore.QObject):
    '''
    signals for a worker
    '''

    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)


class Form(QtCore.QObject):

    def __init__(self, ui_file, esi_client, esi_app, app_info, security, scopes, parent=None):
        super(Form, self).__init__(parent)

        self.threadpool = QtCore.QThreadPool()

        self.esi_client = esi_client
        self.esi_app = esi_app
        self.app_info = app_info
        self.security = security
        self.scopes = scopes

        self.items_model = pandastable.PandasModel()

        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        # Initiate all UI items
        self.showText = self.window.findChild(QPushButton, 'showText')
        self.loginButton = self.window.findChild(QPushButton, 'loginButton')
        self.updateToken = self.window.findChild(QPushButton, 'updateToken')

        self.brokerFee = self.window.findChild(QLineEdit, 'brokerFee')
        self.transactionTax = self.window.findChild(QLineEdit, 'transactionTax')

        self.buyStationID = self.window.findChild(QLineEdit, 'buyStationID')
        self.sellStationID = self.window.findChild(QLineEdit, 'sellStationID')
        self.buyRegionID = self.window.findChild(QLineEdit, 'buyRegionID')
        self.sellRegionID = self.window.findChild(QLineEdit, 'sellRegionID')

        self.minSellPrice = self.window.findChild(QLineEdit, 'minSellPrice')
        self.historySize = self.window.findChild(QLineEdit, 'historySize')
        self.minDailyProfit = self.window.findChild(QLineEdit, 'minDailyProfit')
        self.minISKVolume = self.window.findChild(QLineEdit, 'minISKVolume')
        self.minDaySold = self.window.findChild(QLineEdit, 'minDaySold')
        self.daysNotSold = self.window.findChild(QLineEdit, 'daysNotSold')

        self.refreshURL = self.window.findChild(QPlainTextEdit, 'refreshURL')

        self.buyBuyOrders = self.window.findChild(QComboBox, 'buyBuyOrders')
        self.sellBuyOrders = self.window.findChild(QComboBox, 'sellBuyOrders')
        self.sellToRegion = self.window.findChild(QComboBox, 'sellToRegion')

        self.loginURL = self.window.findChild(QTextBrowser, 'loginURL')

        self.tableTest = self.window.findChild(QTableView, 'tableTest')

        self.compressionTable = self.window.findChild(QTableView, 'compressionTable')
        self.mineralsTable = self.window.findChild(QTableView, 'mineralsTable')
        self.extraTable = self.window.findChild(QTableView, 'extraTable')

        self.minerals = self.window.findChild(QPlainTextEdit, 'minerals')
        self.calculateCompression = self.window.findChild(QPushButton, 'calculateCompression')
        self.refineRate = self.window.findChild(QLineEdit, 'refineRate')

        self.oreType = self.window.findChild(QComboBox, 'oreType')

        # item price boxes
        self.veldsparPrice = self.window.findChild(QLineEdit, 'veldsparPrice')
        self.spodumainPrice = self.window.findChild(QLineEdit, 'spodumainPrice')
        self.scorditePrice = self.window.findChild(QLineEdit, 'scorditePrice')
        self.plagioclasePrice = self.window.findChild(QLineEdit, 'plagioclasePrice')
        self.omberPrice = self.window.findChild(QLineEdit, 'omberPrice')
        self.kernitePrice = self.window.findChild(QLineEdit, 'kernitePrice')
        self.jaspetPrice = self.window.findChild(QLineEdit, 'jaspetPrice')
        self.hemorphitePrice = self.window.findChild(QLineEdit, 'hemorphitePrice')
        self.hedbergitePrice = self.window.findChild(QLineEdit, 'hedbergitePrice')
        self.gneissPrice = self.window.findChild(QLineEdit, 'gneissPrice')
        self.crokitePrice = self.window.findChild(QLineEdit, 'crokitePrice')
        self.darkOchrePrice = self.window.findChild(QLineEdit, 'darkOchrePrice')
        self.bistotPrice = self.window.findChild(QLineEdit, 'bistotPrice')
        self.arkonorPrice = self.window.findChild(QLineEdit, 'arkonorPrice')
        self.mercoxitPrice = self.window.findChild(QLineEdit, 'mercoxitPrice')

        self.oreBuyID = self.window.findChild(QLineEdit, 'oreBuyID')
        self.oreBuyOrders = self.window.findChild(QComboBox, 'oreBuyOrders')
        self.getOrePrices = self.window.findChild(QPushButton, 'getOrePrices')
        self.costMultiplier = self.window.findChild(QLineEdit, 'costMultiplier')

        # connect buttons to the functions
        self.showText.clicked.connect(self.multi_calculate_2)
        self.loginButton.clicked.connect(self.multi_login)
        self.updateToken.clicked.connect(self.multi_refresh_refresh)

        self.tableTest.horizontalHeader().sectionClicked.connect(self.sort_model)

        self.getOrePrices.clicked.connect(self.multi_ore_prices)

        self.calculateCompression.clicked.connect(self.multi_compress)

        self.first_calc = True

    def get_ore_prices(self):
        ore_table = pd.read_csv('ore id.csv', index_col='name')
        region_id = self.oreBuyID.text()
        orders = market.get_from_region(items=ore_table['type id'], region_id=region_id,
                                        client=self.esi_client, app_esi=self.esi_app)
        items = market.find_price(orders, is_buy_order=self.oreBuyOrders.currentText() == "True")

        items['price'] = items['price'] * float(self.costMultiplier.text())

        return items

    def set_ore_prices(self, prices):

        update_text = [self.veldsparPrice.setText,
                       self.spodumainPrice.setText,
                       self.scorditePrice.setText,
                       self.plagioclasePrice.setText,
                       self.omberPrice.setText,
                       self.kernitePrice.setText,
                       self.jaspetPrice.setText,
                       self.hemorphitePrice.setText,
                       self.hedbergitePrice.setText,
                       self.gneissPrice.setText,
                       self.darkOchrePrice.setText,
                       self.crokitePrice.setText,
                       self.bistotPrice.setText,
                       self.arkonorPrice.setText,
                       self.mercoxitPrice.setText]

        counter = 0
        for item in prices['price']:
            update_text[counter](str(item))
            counter += 1

    def multi_ore_prices(self):
        worker = Worker(self.get_ore_prices)
        worker.signals.result.connect(self.set_ore_prices)
        self.threadpool.start(worker)

    def compress_minerals(self):
        """
        :return: returns the tables for the ore, minerals and extra minerals
        """
        minerals = self.minerals.toPlainText().splitlines()
        # We're using regular expressions to allow for different ways of writing down the minerals like
        # Tritanium,1000
        # Tritanium 1000

        mineral_dict = dict([re.split(',| ', i) for i in minerals])

        minerals_df = pd.Series(mineral_dict).to_frame(name='amount').astype(int)
        minerals_df.index.rename(name='mineral', inplace=True)

        refine_rate = float(self.refineRate.text())

        if self.oreType.currentText() == 'nullsec':
            coefficients = np.array([self.spodumainPrice.text(), self.gneissPrice.text(), self.crokitePrice.text(),
                                     self.darkOchrePrice.text(), self.bistotPrice.text(),
                                     self.arkonorPrice.text(), self.mercoxitPrice.text()]).astype(float)
            compression_df, minerals_get_df, extra_df = compression.compress(minerals=minerals_df,
                                                                             refine_rate=refine_rate,
                                                                             coefficients=coefficients,
                                                                             ore_list='nullsec ore.csv')
        elif self.oreType.currentText() == 'all':
            coefficients = np.array([self.veldsparPrice.text(), self.spodumainPrice.text(), self.scorditePrice.text(),
                                     self.plagioclasePrice.text(), self.omberPrice.text(), self.kernitePrice.text(),
                                     self.jaspetPrice.text(), self.hemorphitePrice.text(), self.hedbergitePrice.text(),
                                     self.gneissPrice.text(), self.darkOchrePrice.text(), self.crokitePrice.text(),
                                     self.bistotPrice.text(), self.arkonorPrice.text(),
                                     self.mercoxitPrice.text()]).astype(float)
            compression_df, minerals_get_df, extra_df = compression.compress(minerals=minerals_df,
                                                                             refine_rate=refine_rate,
                                                                             coefficients=coefficients,
                                                                             ore_list='ore.csv')
        else:
            print("ERROR, not correct oretype wtf")

        compression_table = pandastable.PandasModel(compression_df)
        minerals_get_table = pandastable.PandasModel(minerals_get_df)
        extra_table = pandastable.PandasModel(extra_df)

        return [compression_table, minerals_get_table, extra_table]

    def set_mineral_models(self, models):

        self.compressionTable.setModel(models[0])
        self.mineralsTable.setModel(models[1])
        self.extraTable.setModel(models[2])

    def multi_compress(self):
        worker = Worker(self.compress_minerals)
        worker.signals.result.connect(self.set_mineral_models)
        self.threadpool.start(worker)

    def multi_calculate(self):

        worker = Worker(self.calculate)
        self.threadpool.start(worker)

    def multi_login(self):
        worker = Worker(self.login)
        worker.signals.result.connect(self.set_url)
        self.threadpool.start(worker)

    def multi_refresh_refresh(self):
        worker = Worker(self.refresh_refresh)
        worker.signals.result.connect(self.set_refresh)
        self.threadpool.start(worker)

    def multi_sort_model(self, column):
        worker = Worker(self.sort_model, column)
        self.threadpool.start(worker)

    def multi_calculate_2(self):

        arguments = [int(self.sellStationID.text()),
                     # buy_station=int(self.sellStationID.toPlainText()),
                     int(self.sellRegionID.text()),
                     int(self.buyRegionID.text()),
                     float(self.minSellPrice.text()),
                     float(self.minDaySold.text()),
                     float(self.minISKVolume.text()),
                     float(self.minDailyProfit.text()),
                     float(self.brokerFee.text()),
                     float(self.transactionTax.text()),
                     bool(self.buyBuyOrders.currentText() == "True"),
                     bool(self.sellBuyOrders.currentText() == "True"),
                     bool(self.sellToRegion.currentText() == "True"),
                     int(self.historySize.text()),
                     int(self.daysNotSold.text()),
                     self.esi_client,
                     self.esi_app]

        worker = Worker(calculation.main_program, *arguments)
        worker.signals.result.connect(self.set_model)

        self.threadpool.start(worker)

    def set_url(self, url):
        """
        Made so that the URL can set while using multithreading.
        There were some issues with just giving it self.loginURL.setText because it is not implemented in Python
        :param url: url of the url you want to set
        :return: doesn't return anything
        """
        self.loginURL.setText(url)

    def set_model(self, new_items):
        self.items_model = pandastable.PandasModel(new_items.reset_index().rename(index=str, columns={"index": "item"}))
        self.tableTest.setModel(self.items_model)

    def sort_model(self, column):
        """
        sorts the pandas table based on the column.
        """
        self.items_model.sort(column, True)

    def login(self):

        esi_app_create = EsiApp()
        self.esi_app = esi_app_create.get_latest_swagger

        self.security = EsiSecurity(
            redirect_uri=self.app_info['key']['redirect_uri'],
            client_id=self.app_info['key']['client_id'],
            code_verifier=generate_code_verifier()
        )

        self.esi_client = EsiClient(retry_requests=True, headers={'User-Agent': "Bisnesspirate's EVEMarket app"},
                                    raw_body_only=False, security=self.security)

        return self.security.get_auth_uri(state='SomeRandomGeneratedState', scopes=self.scopes)

    def refresh_refresh(self):
        get_url = self.refreshURL.toPlainText()

        refresh_1st_part = get_url.split('/')[-1]
        refresh_token_2nd_part = refresh_1st_part.split('&')[0]
        refresh_token_3rd_part = refresh_token_2nd_part.split('?code=')[-1]

        return self.security.auth(refresh_token_3rd_part)

    def set_refresh(self, tokens):
        refresh_token = tokens['refresh_token']

        self.security.update_token({
            'access_token': '',
            'expires_in': -1,
            'refresh_token': refresh_token
        })

        # self.refreshToken.setPlainText(refresh_token)

        self.app_info['key']['refresh_token'] = refresh_token

        self.app_info.to_csv('appinfo.csv')

        print("refreshed")
