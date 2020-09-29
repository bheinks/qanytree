from functools import partial

from PyQt5.QtWidgets import QTreeView, QMenu
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex


class DictionaryTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = DictionaryTreeModel(['Key', 'Value'])
        self.setModel(self.model)

        # Right click context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)

    def open_menu(self, position):
        menu = QMenu()
        add_key_action = menu.addAction('Add Key')

        # Right click action on item
        model_index = self.indexAt(position)
        if model_index.isValid():
            item = self.model.getItem(model_index)

            delete_key_action = menu.addAction('Delete Key')
            delete_key_action.triggered.connect(partial(
                self.model.deleteItem, item, model_index))
        # Right click action otherwise
        else:
            item = self.model.rootItem

        add_key_action.triggered.connect(partial(self.model.addChild, item))
        add_key_action.triggered.connect(partial(self.expand, model_index))

        menu.exec(self.sender().viewport().mapToGlobal(position))

    def setData(self, data):
        self.model.setupModelData(data)

    def toDict(self):
        return self.model.rootItem.toDict()

    def keyPressEvent(self, e):
        # Delete row on key press
        if e.key() == Qt.Key_Delete:
            indexes = self.selectedIndexes()

            if indexes:
                key_index = indexes[0]
                item = self.model.getItem(key_index)
                self.model.deleteItem(item, key_index)
        else:
            super().keyPressEvent(e)


class DictionaryTreeModel(QAbstractItemModel):
    def __init__(self, headers, data={}, parent=None):
        super().__init__(parent)

        self.rootData = headers
        self.rootItem = None
        self.setupModelData(data)

    def columnCount(self, parent=QModelIndex()):
        return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole and role != Qt.EditRole:
            return None

        item = self.getItem(index)

        return item.data(index.column())

    def flags(self, index=QModelIndex()):
        if not index.isValid():
            return Qt.NoItemFlags

        # Disable editing values of keys with children
        if index.column() != 0 and self.getItem(index).childItems:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()

            if item:
                return item

        return self.rootItem

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            return QModelIndex()

        parentItem = self.getItem(parent)
        if not parentItem:
            return QModelIndex()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)

        return QModelIndex()

    def insertColumns(self, position, columns, parent=QModelIndex()):
        self.beginInsertColumns(parent, position, position + columns - 1)
        success = self.rootItem.insertColumns(position, columns)
        self.endInsertColumns()

        return success

    def insertRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if not parentItem:
            return False

        self.beginInsertRows(parent, position, position + rows - 1)
        success = parentItem.insertChildren(position, rows,
                                            self.rootItem.columnCount())
        self.endInsertRows()

        return success

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = self.getItem(index)
        parentItem = childItem.parent() if childItem else None

        if parentItem == self.rootItem or not parentItem:
            return QModelIndex()

        return self.createIndex(parentItem.childNumber(), 0, parentItem)

    def removeColumns(self, position, columns, parent=QModelIndex()):
        self.beginRemoveColumns(parent, position, position + columns - 1)
        success = self.rootItem.removeColumns(position, columns)
        self.endRemoveColumns()

        if self.rootItem.columnCount() == 0:
            self.removeRows(0, self.rowCount())

        return success

    def removeRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if not parentItem:
            return False

        self.beginRemoveRows(parent, position, position + rows - 1)
        success = parentItem.removeChildren(position, rows)
        self.endRemoveRows()

        return success

    def rowCount(self, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        return parentItem.childCount() if parentItem else 0

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False

        item = self.getItem(index)
        result = item.setData(index.column(), value)

        if result:
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])

        return result

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        if role != Qt.EditRole or orientation != Qt.Horizontal:
            return False

        result = self.rootItem.setData(section, value)
        if result:
            self.headerDataChanged.emit(orientation, section, section)

        return result

    def setupModelData(self, data, parent=None):
        if not parent:
            parent = self.rootItem = DictionaryTreeItem(self.rootData)

        for k, v in data.items():
            if isinstance(v, dict):
                parent.appendChild([k, None])
                self.setupModelData(v, parent.child(parent.childCount() - 1))
            else:
                parent.appendChild([k, v])

        self.layoutChanged().emit()

    def addChild(self, item):
        sibling_keys = [c.data(0) for c in item.childItems]

        i = 1
        while True:
            new_key = f'New Key #{i}'

            if new_key not in sibling_keys:
                break

            i += 1

        item.appendChild([new_key, None])

        # If not root item, clear parent value
        if item != self.rootItem:
            item.setData(1, None)

        self.layoutChanged.emit()

    def deleteItem(self, item, index):
        self.removeRows(item.childNumber(), 1, index.parent())
        self.layoutChanged.emit()


class DictionaryTreeItem:
    def __init__(self, data, parent=None):
        self.itemData = data
        self.parentItem = parent
        self.childItems = []

    def child(self, number):
        try:
            return self.childItems[number]
        except IndexError:
            return None

    def childCount(self):
        return len(self.childItems)

    def childNumber(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        try:
            return self.itemData[column]
        except IndexError:
            return None

    def insertChildren(self, position, count, columns):
        if position < 0 or position > len(self.childItems):
            return False

        for _ in range(count):
            data = [None] * columns
            item = DictionaryTreeItem(data, self)
            self.childItems.insert(position, item)

        return True

    def appendChild(self, data):
        self.childItems.append(DictionaryTreeItem(data, self))

    def insertColumns(self, position, columns):
        if column < 0 or column >= len(self.itemData):
            return False

        for _ in range(columns):
            self.itemData.insert(position, None)

        for child in self.childItems:
            child.insertColumns(position, columns)

        return True

    def parent(self):
        return self.parentItem

    def removeChildren(self, position, count):
        if position < 0 or position + count > len(self.childItems):
            return False

        for _ in range(count):
            self.childItems.pop(position)

        return True

    def removeColumns(self, position, columns):
        if position < 0 or position + columns > len(self.itemData):
            return False

        for _ in range(columns):
            self.itemData.pop(position)

        for child in self.childItems:
            child.removeColumns(position, columns)

        return True

    def setData(self, column, value):
        if column < 0 or column >= len(self.itemData):
            return False

        self.itemData[column] = value

        return True

    def toDict(self, d={}):
        for child in self.childItems:
            child._recurse_dict(d)

        return d

    def _recurse_dict(self, d):
        k, v = self.itemData

        if self.childItems:
            d[k] = {}

            for child in self.childItems:
                child._recurse_dict(d[k])
        else:
            d[k] = v
