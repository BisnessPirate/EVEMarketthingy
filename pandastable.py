import pandas as pd
from PySide2 import QtCore



"""
From https://stackoverflow.com/questions/44603119/how-to-display-a-pandas-data-frame-with-pyqt5
Changed the sort function to if it is sorted to inverse it.
Also made it compatible with Pyside2
"""


class PandasModel(QtCore.QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        self._df = df

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except (IndexError,):
                return None
        elif orientation == QtCore.Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self._df.index.tolist()[section]
            except (IndexError,):
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

        # These are there so that if you sort a sorted column that the sorting gets inversed.

        if temp_df.is_monotonic_decreasing == True:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending=False == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()

        elif temp_df.is_monotonic_increasing == True:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending=True == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()
        else:
            self.layoutAboutToBeChanged.emit()
            self._df.sort_values(colname, ascending=order == QtCore.Qt.AscendingOrder, inplace=True)

            self.layoutChanged.emit()